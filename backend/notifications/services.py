"""Expiry and low-stock alerts.

Who is told: every active user with the admin role (the shop owner and staff).
When:
  * right away - after a sale, or when an admin adds/edits a batch (stock_changed signal)
  * every day  - run_daily_checks(), started by `manage.py check_expiry_stock` or `run_scheduler`
No duplicates: a batch is announced once as "expiring soon" and once as "expired"; a product
is announced as low stock once, until it has been restocked.
"""
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from catalog.models import Product, ProductBatch

from . import push
from .models import Notification

T = Notification.Type

PUSH_TITLES = {
    T.EXPIRED: "Product expired",
    T.EXPIRY_SOON: "Expiring soon",
    T.LOW_STOCK: "Low stock",
}


def shop_admins():
    return list(User.objects.filter(is_active=True, role=User.Role.ADMIN))


def _plural(n, word):
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _notify(ntype, message, product, batch=None, dedupe=None, push_now=True):
    """Create the notification for each admin who hasn't got it yet. Returns how many were created."""
    recipients = []
    for user in shop_admins():
        if dedupe and Notification.objects.filter(user=user, **dedupe).exists():
            continue
        Notification.objects.create(user=user, type=ntype, message=message, product=product, batch=batch)
        recipients.append(user)
    if recipients and push_now:
        data = {"type": ntype, "product_id": product.pk}
        # After the surrounding transaction commits, so a slow push never holds up a sale.
        transaction.on_commit(lambda: push.send_to_users(recipients, PUSH_TITLES[ntype], message, data))
    return len(recipients)


def refresh_stock():
    """Re-count stock for every product with batches (expired batches stop counting on their own day)."""
    for product in Product.objects.filter(batches__isnull=False).distinct():
        product.recalc_stock()


def check_batch(batch, push_now=True):
    """Alert about one batch if it has expired or expires within EXPIRY_WARNING_DAYS."""
    if batch.qty <= 0:
        return 0  # nothing left to sell or throw away
    days = (batch.expiry_date - timezone.localdate()).days
    name = f"{batch.product.name} (batch {batch.batch_no})"
    units = _plural(batch.qty, "unit")
    if days < 0:
        message = f"{name}: {units} expired on {batch.expiry_date:%d %b %Y}. Remove from sale."
        return _notify(T.EXPIRED, message, batch.product, batch, {"type": T.EXPIRED, "batch": batch}, push_now)
    if days <= settings.EXPIRY_WARNING_DAYS:
        when = "today" if days == 0 else f"in {_plural(days, 'day')}"
        message = f"{name}: {units} expire {when} ({batch.expiry_date:%d %b %Y})."
        return _notify(T.EXPIRY_SOON, message, batch.product, batch, {"type": T.EXPIRY_SOON, "batch": batch}, push_now)
    return 0


def check_low_stock(product, push_now=True):
    """Alert when stock is at or below the product's threshold; reset once it is restocked."""
    if not product.is_active:
        return 0
    if product.stock_qty <= product.low_stock_threshold:
        if product.stock_qty == 0:
            message = f"Out of stock: {product.name}."
        else:
            message = (f"Low stock: {product.name} has only {product.stock_qty} left "
                       f"(alert level {product.low_stock_threshold}).")
        return _notify(T.LOW_STOCK, message, product, None,
                       {"type": T.LOW_STOCK, "product": product, "resolved": False}, push_now)
    Notification.objects.filter(type=T.LOW_STOCK, product=product, resolved=False).update(resolved=True)
    return 0


def on_stock_changed(sender, product, batch=None, **kwargs):
    """Signal receiver: runs after a sale or an admin batch edit."""
    check_low_stock(product)
    if batch is not None:
        check_batch(batch)


def run_daily_checks():
    """Full sweep. Returns how many new alerts were created, by kind."""
    refresh_stock()
    expired = soon = low = 0
    for batch in ProductBatch.objects.filter(qty__gt=0).select_related("product"):
        created = check_batch(batch, push_now=False)
        if created:
            if batch.expiry_date < timezone.localdate():
                expired += 1
            else:
                soon += 1
    for product in Product.objects.filter(is_active=True):
        low += 1 if check_low_stock(product, push_now=False) else 0

    if expired or soon or low:  # one summary push instead of one per alert
        parts = [f"{n} {label}" for n, label in ((expired, "expired"), (soon, "expiring soon"), (low, "low stock")) if n]
        transaction.on_commit(
            lambda: push.send_to_users(shop_admins(), "Vetri Bills daily check", ", ".join(parts), {"type": "digest"})
        )
    return {"expired": expired, "expiring_soon": soon, "low_stock": low}
