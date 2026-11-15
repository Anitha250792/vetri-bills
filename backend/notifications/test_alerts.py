import io
import json
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import DeviceToken, User
from catalog.models import Category, Product, ProductBatch
from orders import services as order_services
from orders.models import Cart, CartItem

from . import services
from .models import Notification

T = Notification.Type


@override_settings(PUSH_ENABLED=False, EXPIRY_WARNING_DAYS=7)
class AlertTestBase(APITestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.cat = Category.objects.create(name="Dairy")
        self.admin = User.objects.create_user("owner", "owner@x.com", "Str0ng!Pass1", role="admin")
        self.customer = User.objects.create_user("asha", "asha@x.com", "Str0ng!Pass1")

    def product(self, name="Milk", sku="M1", threshold=10, **kw):
        return Product.objects.create(category=self.cat, name=name, sku=sku, price=Decimal("50"),
                                      low_stock_threshold=threshold, **kw)

    def batch(self, product, days, qty=50, no="B1"):
        return ProductBatch.objects.create(product=product, batch_no=no, qty=qty,
                                           expiry_date=self.today + timedelta(days=days))

    def of(self, ntype, user=None):
        return Notification.objects.filter(user=user or self.admin, type=ntype)


class ExpiryAlertTests(AlertTestBase):
    def test_expiring_within_window_alerts_admin_only(self):
        self.batch(self.product(), days=3)
        n = self.of(T.EXPIRY_SOON)
        self.assertEqual(n.count(), 1)
        self.assertIn("expire in 3 days", n.first().message)
        self.assertEqual(Notification.objects.filter(user=self.customer).count(), 0)

    def test_window_boundaries(self):
        p = self.product()
        self.batch(p, days=7, no="EDGE")        # inside
        self.batch(p, days=8, no="OUTSIDE")     # outside
        self.batch(p, days=0, no="TODAY")       # today counts as expiring
        messages = " | ".join(self.of(T.EXPIRY_SOON).values_list("message", flat=True))
        self.assertIn("EDGE", messages)
        self.assertIn("TODAY", messages)
        self.assertIn("expire today", messages)
        self.assertNotIn("OUTSIDE", messages)

    def test_expired_batch_alerts(self):
        self.batch(self.product(), days=-2)
        n = self.of(T.EXPIRED)
        self.assertEqual(n.count(), 1)
        self.assertIn("expired on", n.first().message)

    def test_empty_batch_is_ignored(self):
        self.batch(self.product(), days=-2, qty=0)
        self.batch(self.product("Curd", "C1"), days=1, qty=0)
        # No expiry alerts for empty batches (the products are rightly reported as out of stock).
        self.assertEqual(Notification.objects.filter(type__in=[T.EXPIRED, T.EXPIRY_SOON]).count(), 0)
        self.assertEqual(Notification.objects.filter(type=T.LOW_STOCK).count(), 2)

    def test_no_duplicates_when_the_daily_job_runs_again(self):
        self.batch(self.product(), days=2)
        before = Notification.objects.count()
        for _ in range(3):
            services.run_daily_checks()
        self.assertEqual(Notification.objects.count(), before)

    def test_batch_gets_one_soon_alert_then_one_expired_alert(self):
        b = self.batch(self.product(), days=2)
        self.assertEqual(self.of(T.EXPIRY_SOON).count(), 1)
        ProductBatch.objects.filter(pk=b.pk).update(expiry_date=self.today - timedelta(days=1))
        services.run_daily_checks()
        services.run_daily_checks()
        self.assertEqual(self.of(T.EXPIRY_SOON).count(), 1)
        self.assertEqual(self.of(T.EXPIRED).count(), 1)

    def test_daily_job_stops_counting_batches_that_expired_overnight(self):
        p = self.product()
        b = self.batch(p, days=1, qty=40)
        self.batch(p, days=60, qty=15, no="B2")
        p.refresh_from_db()
        self.assertEqual(p.stock_qty, 55)
        ProductBatch.objects.filter(pk=b.pk).update(expiry_date=self.today - timedelta(days=1))  # a day passes
        result = services.run_daily_checks()
        p.refresh_from_db()
        self.assertEqual(p.stock_qty, 15)
        self.assertEqual(result["expired"], 1)

    def test_every_admin_is_told(self):
        second = User.objects.create_user("staff", "staff@x.com", "Str0ng!Pass1", role="admin")
        self.batch(self.product(), days=1)
        self.assertEqual(self.of(T.EXPIRY_SOON, second).count(), 1)
        self.assertEqual(self.of(T.EXPIRY_SOON, self.admin).count(), 1)

    def test_command_reports_counts(self):
        p = self.product()
        ProductBatch.objects.bulk_create([  # bulk: skips the instant alerts, so the job finds them
            ProductBatch(product=p, batch_no="X", qty=30, expiry_date=self.today + timedelta(days=2)),
            ProductBatch(product=p, batch_no="Y", qty=30, expiry_date=self.today - timedelta(days=2)),
        ])
        out = io.StringIO()
        call_command("check_expiry_stock", stdout=out)
        self.assertIn("1 expired, 1 expiring within 7 days", out.getvalue())


class LowStockAlertTests(AlertTestBase):
    def test_low_stock_alert_when_at_or_below_threshold(self):
        self.batch(self.product(threshold=10), days=90, qty=10)
        n = self.of(T.LOW_STOCK)
        self.assertEqual(n.count(), 1)
        self.assertIn("only 10 left", n.first().message)

    def test_no_alert_above_threshold(self):
        self.batch(self.product(threshold=10), days=90, qty=11)
        self.assertEqual(self.of(T.LOW_STOCK).count(), 0)

    def test_out_of_stock_message(self):
        self.batch(self.product(), days=90, qty=0)
        self.assertIn("Out of stock", self.of(T.LOW_STOCK).first().message)

    def test_one_alert_until_restocked_then_alerts_again(self):
        p = self.product(threshold=10)
        b = self.batch(p, days=90, qty=5)
        services.run_daily_checks()
        self.assertEqual(self.of(T.LOW_STOCK).count(), 1)  # no repeat

        b.qty = 80
        b.save()  # restocked
        self.assertTrue(self.of(T.LOW_STOCK).get().resolved)

        b.qty = 3
        b.save()  # runs low again
        self.assertEqual(self.of(T.LOW_STOCK).count(), 2)

    def test_inactive_product_is_not_alerted(self):
        self.batch(self.product(is_active=False), days=90, qty=1)
        self.assertEqual(self.of(T.LOW_STOCK).count(), 0)

    def test_product_without_batches_uses_its_own_stock(self):
        self.product(stock_qty=4)
        services.run_daily_checks()
        self.assertEqual(self.of(T.LOW_STOCK).count(), 1)

    def test_alert_after_a_sale_brings_stock_down(self):
        p = self.product(threshold=10)
        self.batch(p, days=90, qty=14)
        self.assertEqual(self.of(T.LOW_STOCK).count(), 0)

        cart = Cart.objects.create(user=self.customer)
        CartItem.objects.create(cart=cart, product=p, quantity=6)
        order = order_services.create_order_from_cart(self.customer)
        payment = order_services.create_payment(order)
        order_services.complete_payment(payment, "pay_1", "sig")

        p.refresh_from_db()
        self.assertEqual(p.stock_qty, 8)
        self.assertIn("only 8 left", self.of(T.LOW_STOCK).get().message)


class NotificationApiTests(AlertTestBase):
    def setUp(self):
        super().setUp()
        p = self.product()
        self.batch(p, days=2, qty=5)  # creates: expiring soon + low stock
        self.client.force_authenticate(self.admin)

    def test_list_unread_count_and_filters(self):
        r = self.client.get(reverse("notification-list"))
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(self.client.get(reverse("notification-unread")).data["unread"], 2)
        r = self.client.get(reverse("notification-list"), {"type": "low_stock"})
        self.assertEqual(r.data["count"], 1)

    def test_mark_read_and_read_all(self):
        first = Notification.objects.filter(user=self.admin).first()
        r = self.client.post(reverse("notification-read", args=[first.pk]))
        self.assertTrue(r.data["is_read"])
        self.assertEqual(self.client.get(reverse("notification-unread")).data["unread"], 1)
        r = self.client.post(reverse("notification-read-all"))
        self.assertEqual(r.data["updated"], 1)
        self.assertEqual(self.client.get(reverse("notification-list"), {"is_read": "false"}).data["count"], 0)

    def test_users_only_see_their_own(self):
        other = User.objects.create_user("staff", "s@x.com", "Str0ng!Pass1", role="admin")
        # `other` was created after the batch, so has none yet
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get(reverse("notification-list")).data["count"], 0)
        mine = Notification.objects.filter(user=self.admin).first()
        self.assertEqual(self.client.post(reverse("notification-read", args=[mine.pk])).status_code, 404)

    def test_customer_sees_none_and_anonymous_is_refused(self):
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.get(reverse("notification-list")).data["count"], 0)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(reverse("notification-list")).status_code, 401)


class ReportTests(AlertTestBase):
    def setUp(self):
        super().setUp()
        self.milk = self.product("Milk", "M1")
        self.batch(self.milk, days=-3, qty=7, no="OLD")
        self.batch(self.milk, days=2, qty=30, no="SOON")
        self.batch(self.milk, days=40, qty=20, no="LATER")
        self.soap = self.product("Soap", "S1", threshold=10)
        self.batch(self.soap, days=300, qty=4, no="S")

    def test_report_contents(self):
        self.client.force_authenticate(self.admin)
        r = self.client.get(reverse("expiry-report"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["summary"], {"expired": 1, "expiring_soon": 1, "low_stock": 1})
        self.assertEqual(r.data["expired"][0]["batch_no"], "OLD")
        self.assertEqual(r.data["expired"][0]["days_to_expiry"], -3)
        self.assertEqual(r.data["expiring_soon"][0]["product_name"], "Milk")
        self.assertEqual(r.data["low_stock"][0]["name"], "Soap")

    def test_days_parameter_widens_the_window(self):
        self.client.force_authenticate(self.admin)
        r = self.client.get(reverse("expiry-report"), {"days": 45})
        self.assertEqual([b["batch_no"] for b in r.data["expiring_soon"]], ["SOON", "LATER"])
        self.assertEqual(self.client.get(reverse("expiry-report"), {"days": "abc"}).status_code, 400)
        self.assertEqual(self.client.get(reverse("expiry-report"), {"days": 999}).status_code, 400)

    def test_admin_only(self):
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.get(reverse("expiry-report")).status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(reverse("expiry-report")).status_code, 401)


class PushTests(AlertTestBase):
    def fake_expo(self, statuses):
        body = json.dumps({"data": statuses}).encode()
        response = mock.MagicMock()
        response.read.return_value = body
        response.__enter__.return_value = response
        return mock.patch("notifications.push.urllib.request.urlopen", return_value=response)

    @override_settings(PUSH_ENABLED=True)
    def test_push_sent_to_admin_devices_and_dead_tokens_removed(self):
        DeviceToken.objects.create(user=self.admin, token="ExponentPushToken[good]")
        DeviceToken.objects.create(user=self.admin, token="ExponentPushToken[gone]")
        DeviceToken.objects.create(user=self.customer, token="ExponentPushToken[customer]")
        statuses = [{"status": "ok"}, {"status": "error", "details": {"error": "DeviceNotRegistered"}}]
        with self.fake_expo(statuses) as urlopen, self.captureOnCommitCallbacks(execute=True):
            self.batch(self.product(), days=2)
        sent = json.loads(urlopen.call_args.args[0].data)
        self.assertEqual({m["to"] for m in sent}, {"ExponentPushToken[good]", "ExponentPushToken[gone]"})
        self.assertEqual(sent[0]["title"], "Expiring soon")
        self.assertFalse(DeviceToken.objects.filter(token="ExponentPushToken[gone]").exists())
        self.assertTrue(DeviceToken.objects.filter(token="ExponentPushToken[customer]").exists())

    @override_settings(PUSH_ENABLED=True)
    def test_daily_job_sends_one_summary_push(self):
        DeviceToken.objects.create(user=self.admin, token="ExponentPushToken[good]")
        p = self.product()
        ProductBatch.objects.bulk_create([
            ProductBatch(product=p, batch_no=f"B{i}", qty=30, expiry_date=self.today + timedelta(days=i))
            for i in range(1, 4)
        ])
        with self.fake_expo([{"status": "ok"}]) as urlopen, self.captureOnCommitCallbacks(execute=True):
            services.run_daily_checks()
        self.assertEqual(urlopen.call_count, 1)
        sent = json.loads(urlopen.call_args.args[0].data)
        self.assertEqual(len(sent), 1)
        self.assertIn("3 expiring soon", sent[0]["body"])

    @override_settings(PUSH_ENABLED=True)
    def test_network_failure_never_breaks_the_stock_update(self):
        DeviceToken.objects.create(user=self.admin, token="ExponentPushToken[good]")
        with mock.patch("notifications.push.urllib.request.urlopen", side_effect=OSError("offline")), \
                self.captureOnCommitCallbacks(execute=True):
            self.batch(self.product(), days=2)  # must not raise
        self.assertEqual(self.of(T.EXPIRY_SOON).count(), 1)

    def test_invalid_tokens_are_not_sent(self):
        DeviceToken.objects.create(user=self.admin, token="not-an-expo-token")
        with override_settings(PUSH_ENABLED=True), mock.patch("notifications.push.urllib.request.urlopen") as urlopen:
            with self.captureOnCommitCallbacks(execute=True):
                self.batch(self.product(), days=2)
        urlopen.assert_not_called()
