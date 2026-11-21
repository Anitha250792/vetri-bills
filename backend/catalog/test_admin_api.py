from datetime import timedelta

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from catalog.models import Category, Product, ProductBatch
from notifications.models import Notification

T = Notification.Type


@override_settings(PUSH_ENABLED=False, EXPIRY_WARNING_DAYS=7)
class AdminProductApiTests(APITestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.cat = Category.objects.create(name="Dairy")
        self.admin = User.objects.create_user("owner", "owner@x.com", "Str0ng!Pass1", role="admin")
        self.customer = User.objects.create_user("asha", "asha@x.com", "Str0ng!Pass1")
        self.client.force_authenticate(self.admin)

    def new_product(self, qty=4, days=3, **extra):
        body = {
            "name": "Fresh Curd", "category": self.cat.id, "price": "30.00", "mrp": "35.00",
            "tax_percent": "5", "low_stock_threshold": 10,
            "initial_batch": {"batch_no": "B1", "qty": qty, "expiry_date": str(self.today + timedelta(days=days))},
        }
        body.update(extra)
        return self.client.post("/api/admin/products/", body, format="json")

    def alerts(self, ntype):
        return Notification.objects.filter(type=ntype, resolved=False)

    def test_only_admin_can_use_it(self):
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.get("/api/admin/products/").status_code, 403)
        self.assertEqual(self.new_product().status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/admin/products/").status_code, 401)

    def test_new_product_with_stock_and_expiry_raises_alerts(self):
        res = self.new_product(qty=4, days=3)
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data["stock_qty"], 4)
        self.assertTrue(res.data["sku"].startswith("VB-"))
        product = Product.objects.get(pk=res.data["id"])
        self.assertEqual(product.batches.count(), 1)
        self.assertEqual(self.alerts(T.EXPIRY_SOON).filter(product=product).count(), 1)  # expires in 3 days
        self.assertEqual(self.alerts(T.LOW_STOCK).filter(product=product).count(), 1)  # 4 <= 10

    def test_healthy_new_product_raises_no_alert(self):
        res = self.new_product(qty=100, days=90)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(Notification.objects.count(), 0)

    def test_product_without_stock_alerts_out_of_stock(self):
        res = self.client.post(
            "/api/admin/products/",
            {"name": "Ghee", "category": self.cat.id, "price": "500"}, format="json",
        )
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(self.alerts(T.LOW_STOCK).count(), 1)

    def test_restock_resolves_low_stock(self):
        pid = self.new_product(qty=4, days=90).data["id"]
        self.assertEqual(self.alerts(T.LOW_STOCK).count(), 1)
        res = self.client.post(
            f"/api/admin/products/{pid}/batches/",
            {"qty": 60, "expiry_date": str(self.today + timedelta(days=60))}, format="json",
        )
        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(res.data["batch_no"])  # generated
        self.assertEqual(Product.objects.get(pk=pid).stock_qty, 64)
        self.assertEqual(self.alerts(T.LOW_STOCK).count(), 0)

    def test_editing_expiry_to_past_raises_expired_alert(self):
        pid = self.new_product(qty=50, days=90).data["id"]
        batch = ProductBatch.objects.get(product_id=pid)
        res = self.client.patch(
            f"/api/admin/batches/{batch.id}/", {"expiry_date": str(self.today - timedelta(days=1))}, format="json"
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(self.alerts(T.EXPIRED).filter(product_id=pid).count(), 1)
        self.assertEqual(Product.objects.get(pk=pid).stock_qty, 0)  # expired stock is not sellable

    def test_duplicate_batch_number_rejected(self):
        pid = self.new_product(qty=50, days=90).data["id"]
        res = self.client.post(
            f"/api/admin/products/{pid}/batches/",
            {"batch_no": "B1", "qty": 5, "expiry_date": str(self.today + timedelta(days=30))}, format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("batch_no", res.data)

    def test_validation(self):
        self.assertEqual(self.new_product(price="0").status_code, 400)
        self.assertEqual(self.new_product(price="50", mrp="40").status_code, 400)
        self.assertEqual(self.new_product(sku="VB-0001").status_code, 201)
        self.assertEqual(self.new_product(sku="VB-0001").status_code, 400)  # SKU already used

    def test_delete_batch_updates_stock_and_delete_product_hides_it(self):
        pid = self.new_product(qty=50, days=90).data["id"]
        ProductBatch.objects.create(product_id=pid, batch_no="B2", qty=5, expiry_date=self.today + timedelta(days=30))
        batch = ProductBatch.objects.get(product_id=pid, batch_no="B2")
        self.assertEqual(self.client.delete(f"/api/admin/batches/{batch.id}/").status_code, 204)
        self.assertEqual(Product.objects.get(pk=pid).stock_qty, 50)
        self.assertEqual(self.client.delete(f"/api/admin/products/{pid}/").status_code, 200)
        self.assertFalse(Product.objects.get(pk=pid).is_active)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(f"/api/products/{pid}/").status_code, 404)

    def test_list_includes_hidden_and_searches(self):
        pid = self.new_product().data["id"]
        self.client.delete(f"/api/admin/products/{pid}/")
        self.assertEqual(len(self.client.get("/api/admin/products/?search=curd").data), 1)
        self.assertEqual(len(self.client.get("/api/admin/products/?is_active=1").data), 0)
