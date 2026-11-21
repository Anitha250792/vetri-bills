"""Checkout, payment and stock logic.

Flow:
  1. create_order_from_cart()  - checks stock, copies price/tax into OrderItem
  2. create_payment()          - Razorpay order (or a mock one while using dummy keys)
  3. complete_payment()        - after the signature is verified: take stock from the
                                 batches that expire first (FEFO), all in one transaction
  4. create_bill()             - PDF saved in the backend

Prices are BEFORE tax: tax = line_total * rate / 100 and total = subtotal + tax.
Stock is taken when payment succeeds, not at checkout, so abandoned carts never block stock.
"""
import base64
import hashlib
import hmac
import json
import secrets
import urllib.error
import urllib.request
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from catalog.models import Product

from .bill_pdf import build_bill_pdf
from .models import Bill, Cart, Order, OrderItem, Payment

TWOPLACES = Decimal("0.01")


def money(value):
    return Decimal(value).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def line_tax(line_total, tax_percent):
    """Tax added on top of a line's pre-tax amount."""
    return money(Decimal(line_total) * Decimal(tax_percent) / 100)


class CheckoutError(Exception):
    def __init__(self, message, details=None):
        super().__init__(message)
        self.message = message
        self.details = details or []


class InsufficientStock(Exception):
    def __init__(self, product, available):
        super().__init__(f"Only {available} of '{product.name}' left")
        self.product = product
        self.available = available


# ------------------------------------------------------------- order ------
@transaction.atomic
def create_order_from_cart(user, shipping_address=""):
    cart = Cart.objects.filter(user=user).first()
    items = list(cart.items.select_related("product")) if cart else []
    if not items:
        raise CheckoutError("Your cart is empty.")

    problems = []
    for item in items:
        product = item.product
        if not product.is_active:
            problems.append({"product_id": product.pk, "name": product.name, "available": 0,
                             "requested": item.quantity})
        elif item.quantity > product.stock_qty:
            problems.append({"product_id": product.pk, "name": product.name,
                             "available": product.stock_qty, "requested": item.quantity})
    if problems:
        raise CheckoutError("Some items are not available in the requested quantity.", problems)

    # A new checkout replaces any older unpaid order.
    Order.objects.filter(user=user, status=Order.Status.PENDING).update(status=Order.Status.CANCELLED)

    shipping_address = (shipping_address or "").strip()
    if not shipping_address:
        raise CheckoutError("Please enter your delivery address.")
    order = Order.objects.create(user=user, shipping_address=shipping_address)
    subtotal = tax_total = Decimal("0")
    for item in items:
        product = item.product
        line_total = money(product.price * item.quantity)
        tax = line_tax(line_total, product.tax_percent)
        OrderItem.objects.create(
            order=order, product=product, product_name=product.name, unit_price=product.price,
            tax_percent=product.tax_percent, quantity=item.quantity, line_total=line_total,
        )
        subtotal += line_total
        tax_total += tax
    order.subtotal = subtotal
    order.tax_total = tax_total
    order.total = subtotal + tax_total
    order.save(update_fields=["total", "tax_total", "subtotal"])
    return order


# ----------------------------------------------------------- payment ------
def expected_signature(razorpay_order_id, razorpay_payment_id):
    message = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
    return hmac.new(settings.RAZORPAY_KEY_SECRET.encode(), message, hashlib.sha256).hexdigest()


def verify_signature(razorpay_order_id, razorpay_payment_id, signature):
    return hmac.compare_digest(expected_signature(razorpay_order_id, razorpay_payment_id), signature or "")


def _razorpay_create_order(amount_paise, receipt):
    """Calls Razorpay's Orders API (used when MOCK_PAYMENTS=0 and real test keys are set)."""
    credentials = base64.b64encode(
        f"{settings.RAZORPAY_KEY_ID}:{settings.RAZORPAY_KEY_SECRET}".encode()
    ).decode()
    request = urllib.request.Request(
        "https://api.razorpay.com/v1/orders",
        data=json.dumps({"amount": amount_paise, "currency": "INR", "receipt": receipt}).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Basic {credentials}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read())["id"]
    except (urllib.error.URLError, KeyError, ValueError) as exc:
        raise CheckoutError("Could not start the payment. Please try again.") from exc


def create_payment(order):
    amount_paise = int(order.total * 100)
    if settings.MOCK_PAYMENTS:
        razorpay_order_id = f"order_mock_{secrets.token_hex(8)}"
    else:
        razorpay_order_id = _razorpay_create_order(amount_paise, receipt=f"VB{order.pk}")
    return Payment.objects.create(
        order=order, provider_order_id=razorpay_order_id, amount=order.total, status="created"
    )


def payment_payload(payment):
    """What the mobile/web app needs to open the Razorpay checkout."""
    return {
        "provider": "razorpay",
        "key_id": settings.RAZORPAY_KEY_ID,
        "razorpay_order_id": payment.provider_order_id,
        "amount": int(payment.amount * 100),
        "currency": "INR",
        "mock": settings.MOCK_PAYMENTS,
    }


# ------------------------------------------------------------- stock ------
def deduct_stock(product_id, qty):
    """Take `qty` units from the batches that expire first. Raises InsufficientStock."""
    product = Product.objects.select_for_update().get(pk=product_id)
    if product.batches.exists():
        batches = list(
            product.batches.select_for_update()
            .filter(qty__gt=0, expiry_date__gte=timezone.localdate())
            .order_by("expiry_date")
        )
        available = sum(b.qty for b in batches)
        if available < qty:
            raise InsufficientStock(product, available)
        remaining = qty
        for batch in batches:
            take = min(batch.qty, remaining)
            batch.qty -= take
            batch.save()  # also refreshes product.stock_qty
            remaining -= take
            if not remaining:
                break
    else:
        if product.stock_qty < qty:
            raise InsufficientStock(product, product.stock_qty)
        product.stock_qty -= qty
        product.save(update_fields=["stock_qty", "updated_at"])


@transaction.atomic
def complete_payment(payment, razorpay_payment_id, signature):
    """Mark the order paid and take stock. Returns the order; status FAILED means the
    stock ran out between checkout and payment (the money must be refunded)."""
    order = Order.objects.select_for_update().get(pk=payment.order_id)
    if order.status == Order.Status.PAID:  # verify called twice: nothing to do
        return order

    payment.provider_payment_id = razorpay_payment_id
    payment.signature = signature
    try:
        with transaction.atomic():  # all-or-nothing for the whole order
            for item in order.items.all():
                deduct_stock(item.product_id, item.quantity)
    except InsufficientStock:
        order.status = Order.Status.FAILED
        payment.status = "needs_refund"
    else:
        order.status = Order.Status.PAID
        payment.status = "paid"
    order.save(update_fields=["status"])
    payment.save()
    return order


# -------------------------------------------------------------- bill ------
def create_bill(order):
    existing = Bill.objects.filter(order=order).first()
    if existing:
        return existing
    created = timezone.localtime(order.created_at)
    bill = Bill.objects.create(order=order, bill_no=f"VB-{created:%Y%m%d}-{order.pk:06d}")
    bill.pdf_file.save(f"{bill.bill_no}.pdf", ContentFile(build_bill_pdf(bill)), save=True)
    return bill


def clear_cart(user):
    Cart.objects.filter(user=user).delete()
