import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from catalog.models import Category, Product, ProductBatch

from .models import Bill, Order

MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA, MOCK_PAYMENTS=True)
class PurchaseFlowTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        today = timezone.localdate()
        cat = Category.objects.create(name="Dairy")
        self.milk = Product.objects.create(category=cat, name="Milk 1L", sku="M1", price=Decimal("105.00"),
                                           tax_percent=Decimal("5"))
        self.soap = Product.objects.create(category=cat, name="Soap", sku="S1", price=Decimal("50.00"),
                                           tax_percent=Decimal("18"))
        self.old = ProductBatch.objects.create(product=self.milk, batch_no="OLD", qty=3,
                                               expiry_date=today + timedelta(days=2))
        self.new = ProductBatch.objects.create(product=self.milk, batch_no="NEW", qty=10,
                                               expiry_date=today + timedelta(days=20))
        ProductBatch.objects.create(product=self.soap, batch_no="S", qty=5, expiry_date=today + timedelta(days=300))
        self.user = User.objects.create_user("asha", "asha@example.com", "Str0ng!Pass1", first_name="Asha")
        self.other = User.objects.create_user("ravi", "ravi@example.com", "Str0ng!Pass1")
        self.client.force_authenticate(self.user)

    def add(self, product, qty=1):
        return self.client.post(reverse("cart-add"), {"product_id": product.pk, "quantity": qty})

    def pay(self):
        """checkout -> mock pay -> verify. Returns the verify response."""
        checkout = self.client.post(reverse("checkout"), {"shipping_address": "12 Main St, Tambaram"})
        self.assertEqual(checkout.status_code, 201, checkout.data)
        rp_order = checkout.data["payment"]["razorpay_order_id"]
        proof = self.client.post(reverse("payment-mock"), {"razorpay_order_id": rp_order}).data
        return checkout, self.client.post(reverse("payment-verify"), proof)

    # ---- cart & wishlist -------------------------------------------------
    def test_cart_add_accumulate_update_remove(self):
        self.assertEqual(self.add(self.milk, 2).status_code, 201)
        r = self.add(self.milk, 3)
        self.assertEqual(r.data["item_count"], 5)
        r = self.client.patch(reverse("cart-item", args=[self.milk.pk]), {"quantity": 1})
        self.assertEqual(r.data["item_count"], 1)
        self.assertEqual(Decimal(r.data["total"]), Decimal("105.00"))
        r = self.client.delete(reverse("cart-item", args=[self.milk.pk]))
        self.assertEqual(r.data["items"], [])

    def test_cannot_add_more_than_stock(self):
        r = self.add(self.milk, 14)  # stock is 13
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["available"], 13)

    def test_cart_requires_login_and_is_private(self):
        self.add(self.milk)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(reverse("cart")).data["items"], [])
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(reverse("cart")).status_code, 401)

    def test_wishlist_toggle(self):
        r = self.client.post(reverse("wishlist-toggle"), {"product_id": self.soap.pk})
        self.assertTrue(r.data["wishlisted"])
        self.assertEqual(len(self.client.get(reverse("wishlist")).data), 1)
        r = self.client.post(reverse("wishlist-toggle"), {"product_id": self.soap.pk})
        self.assertFalse(r.data["wishlisted"])
        self.assertEqual(len(self.client.get(reverse("wishlist")).data), 0)

    # ---- checkout & payment ---------------------------------------------
    def test_empty_cart_cannot_checkout(self):
        self.assertEqual(self.client.post(reverse("checkout")).status_code, 400)

    def test_full_purchase_flow(self):
        self.add(self.milk, 4)  # 3 from OLD batch, 1 from NEW (earliest expiry first)
        self.add(self.soap, 2)
        checkout, verify = self.pay()
        self.assertEqual(verify.status_code, 200, verify.data)

        order = verify.data["order"]
        self.assertEqual(order["status"], "paid")
        # 4 x 105 + 2 x 50 = 520 incl. tax; tax = 420*5/105 + 100*18/118
        self.assertEqual(Decimal(order["total"]), Decimal("520.00"))
        self.assertEqual(Decimal(order["tax_total"]), Decimal("35.25"))
        self.assertEqual(Decimal(order["subtotal"]), Decimal("484.75"))

        self.old.refresh_from_db(); self.new.refresh_from_db()
        self.assertEqual((self.old.qty, self.new.qty), (0, 9))
        self.milk.refresh_from_db(); self.soap.refresh_from_db()
        self.assertEqual((self.milk.stock_qty, self.soap.stock_qty), (9, 3))
        self.assertEqual(self.client.get(reverse("cart")).data["items"], [])  # cart cleared

    def test_bad_signature_is_rejected_and_stock_untouched(self):
        self.add(self.milk, 1)
        checkout = self.client.post(reverse("checkout"))
        r = self.client.post(reverse("payment-verify"), {
            "razorpay_order_id": checkout.data["payment"]["razorpay_order_id"],
            "razorpay_payment_id": "pay_fake", "razorpay_signature": "0" * 64,
        })
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Order.objects.get(pk=checkout.data["order"]["id"]).status, "pending")
        self.milk.refresh_from_db()
        self.assertEqual(self.milk.stock_qty, 13)

    def test_verify_twice_does_not_deduct_twice(self):
        self.add(self.milk, 2)
        checkout = self.client.post(reverse("checkout"))
        rp = checkout.data["payment"]["razorpay_order_id"]
        proof = self.client.post(reverse("payment-mock"), {"razorpay_order_id": rp}).data
        self.assertEqual(self.client.post(reverse("payment-verify"), proof).status_code, 200)
        self.assertEqual(self.client.post(reverse("payment-verify"), proof).status_code, 200)
        self.milk.refresh_from_db()
        self.assertEqual(self.milk.stock_qty, 11)
        self.assertEqual(Bill.objects.count(), 1)

    def test_stock_sold_out_between_checkout_and_payment(self):
        self.add(self.milk, 10)
        checkout = self.client.post(reverse("checkout"))
        ProductBatch.objects.filter(product=self.milk).update(qty=0)  # someone else bought it all
        self.milk.recalc_stock()
        rp = checkout.data["payment"]["razorpay_order_id"]
        proof = self.client.post(reverse("payment-mock"), {"razorpay_order_id": rp}).data
        r = self.client.post(reverse("payment-verify"), proof)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(Order.objects.get(pk=checkout.data["order"]["id"]).status, "failed")
        self.assertEqual(Bill.objects.count(), 0)

    def test_checkout_rejects_when_stock_is_short(self):
        self.add(self.soap, 5)
        ProductBatch.objects.filter(product=self.soap).update(qty=2)
        self.soap.recalc_stock()
        r = self.client.post(reverse("checkout"))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["items"][0]["available"], 2)

    def test_expired_batch_is_never_sold(self):
        self.old.expiry_date = timezone.localdate() - timedelta(days=1)
        self.old.save()  # now only 10 sellable
        self.assertEqual(self.add(self.milk, 11).status_code, 400)

    def test_cannot_verify_someone_elses_payment(self):
        self.add(self.milk, 1)
        checkout = self.client.post(reverse("checkout"))
        rp = checkout.data["payment"]["razorpay_order_id"]
        self.client.force_authenticate(self.other)
        r = self.client.post(reverse("payment-verify"), {
            "razorpay_order_id": rp, "razorpay_payment_id": "x", "razorpay_signature": "y"})
        self.assertEqual(r.status_code, 404)

    def test_new_checkout_cancels_old_pending_order(self):
        self.add(self.milk, 1)
        first = self.client.post(reverse("checkout")).data["order"]["id"]
        self.client.post(reverse("checkout"))
        self.assertEqual(Order.objects.get(pk=first).status, "cancelled")

    # ---- bills ------------------------------------------------------------
    def test_bill_is_saved_listed_and_downloadable_as_pdf(self):
        self.add(self.milk, 1)
        _, verify = self.pay()
        bill_id = verify.data["bill"]["id"]
        self.assertTrue(verify.data["bill"]["bill_no"].startswith("VB-"))

        listing = self.client.get(reverse("bill-list"))
        self.assertEqual(listing.data["count"], 1)

        pdf = self.client.get(reverse("bill-download", args=[bill_id]))
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf["Content-Type"], "application/pdf")
        content = b"".join(pdf.streaming_content)
        self.assertTrue(content.startswith(b"%PDF"))
        self.assertGreater(len(content), 2000)

    def test_bill_does_not_change_when_price_changes_later(self):
        self.add(self.milk, 1)
        _, verify = self.pay()
        self.milk.price = Decimal("999.00")
        self.milk.save()
        order = self.client.get(reverse("order-detail", args=[verify.data["order"]["id"]])).data
        self.assertEqual(Decimal(order["items"][0]["unit_price"]), Decimal("105.00"))

    def test_other_users_cannot_download_a_bill(self):
        self.add(self.milk, 1)
        _, verify = self.pay()
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(reverse("bill-download", args=[verify.data["bill"]["id"]])).status_code, 404)
        self.assertEqual(self.client.get(reverse("bill-list")).data["count"], 0)

    def test_mock_pay_disabled_when_not_in_mock_mode(self):
        self.add(self.milk, 1)
        checkout = self.client.post(reverse("checkout"))
        with self.settings(MOCK_PAYMENTS=False):
            r = self.client.post(reverse("payment-mock"),
                                 {"razorpay_order_id": checkout.data["payment"]["razorpay_order_id"]})
        self.assertEqual(r.status_code, 404)
