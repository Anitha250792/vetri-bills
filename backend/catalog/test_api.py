from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import Category, Product, ProductBatch


class CatalogTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        today = timezone.localdate()
        cls.dairy = Category.objects.create(name="Dairy")
        cls.snacks = Category.objects.create(name="Snacks")
        cls.milk = Product.objects.create(category=cls.dairy, name="Milk 1L", sku="M1", price=60, mrp=66)
        cls.chips = Product.objects.create(category=cls.snacks, name="Chips", sku="C1", price=20)
        cls.hidden = Product.objects.create(category=cls.snacks, name="Hidden", sku="H1", price=5, is_active=False)
        ProductBatch.objects.create(product=cls.milk, batch_no="OLD", qty=5, expiry_date=today - timedelta(days=1))
        ProductBatch.objects.create(product=cls.milk, batch_no="NEW", qty=30, expiry_date=today + timedelta(days=4))
        ProductBatch.objects.create(product=cls.chips, batch_no="X", qty=3, expiry_date=today + timedelta(days=90))

    def test_list_is_public_paginated_and_hides_inactive(self):
        r = self.client.get(reverse("product-list"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 2)
        self.assertEqual({p["name"] for p in r.data["results"]}, {"Milk 1L", "Chips"})

    def test_pagination_page_size(self):
        for i in range(15):
            Product.objects.create(category=self.dairy, name=f"Extra {i}", sku=f"E{i}", price=1)
        r = self.client.get(reverse("product-list"))
        self.assertEqual(len(r.data["results"]), 12)
        self.assertIsNotNone(r.data["next"])

    def test_search_and_category_filter(self):
        r = self.client.get(reverse("product-list"), {"search": "milk"})
        self.assertEqual([p["name"] for p in r.data["results"]], ["Milk 1L"])
        r = self.client.get(reverse("product-list"), {"category": "snacks"})
        self.assertEqual([p["name"] for p in r.data["results"]], ["Chips"])

    def test_price_filter_and_ordering(self):
        r = self.client.get(reverse("product-list"), {"max_price": 30})
        self.assertEqual([p["name"] for p in r.data["results"]], ["Chips"])
        r = self.client.get(reverse("product-list"), {"ordering": "-price"})
        self.assertEqual(r.data["results"][0]["name"], "Milk 1L")

    def test_stock_excludes_expired_batches(self):
        self.milk.refresh_from_db()
        self.assertEqual(self.milk.stock_qty, 30)  # 5 expired units not sellable
        self.chips.refresh_from_db()
        self.assertTrue(self.chips.is_low_stock)  # 3 <= threshold 10

    def test_detail_shows_expiry_and_only_sellable_batches(self):
        r = self.client.get(reverse("product-detail", args=[self.milk.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["discount_percent"], 9)
        self.assertEqual([b["batch_no"] for b in r.data["batches"]], ["NEW"])
        self.assertEqual(r.data["nearest_expiry"], self.milk.nearest_expiry.isoformat())

    def test_inactive_product_detail_404(self):
        self.assertEqual(self.client.get(reverse("product-detail", args=[self.hidden.pk])).status_code, 404)

    def test_categories_with_counts(self):
        r = self.client.get(reverse("category-list"))
        counts = {c["name"]: c["product_count"] for c in r.data}
        self.assertEqual(counts, {"Dairy": 1, "Snacks": 1})

    def test_docs_schema_generates(self):
        self.assertEqual(self.client.get(reverse("schema")).status_code, 200)
