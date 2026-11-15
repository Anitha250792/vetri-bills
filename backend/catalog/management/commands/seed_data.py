"""Seed demo data: python manage.py seed_data [--reset]

Creates an admin, a demo customer, 6 categories and 30 products. Each product gets
1-2 batches; a few batches are set to expire soon or already be expired, and a few
products are low on stock, so the Day 3 expiry / low-stock jobs have something to find.
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from catalog.models import Category, Product, ProductBatch

# category -> [(name, price, mrp, tax %, shelf life days)]
CATALOG = {
    "Dairy & Eggs": [
        ("Full Cream Milk 1L", 62, 66, 5, 5),
        ("Curd 400g", 38, 40, 5, 10),
        ("Paneer 200g", 90, 100, 5, 14),
        ("Salted Butter 100g", 56, 60, 12, 90),
        ("Farm Eggs (12 pack)", 84, 90, 0, 21),
    ],
    "Bakery": [
        ("Sandwich Bread 400g", 45, 50, 5, 4),
        ("Whole Wheat Bread 400g", 52, 55, 5, 4),
        ("Chocolate Muffin", 30, 35, 18, 6),
        ("Veg Puff", 25, 25, 5, 2),
        ("Fruit Cake 250g", 120, 135, 18, 15),
    ],
    "Snacks": [
        ("Potato Chips 90g", 20, 20, 12, 120),
        ("Salted Peanuts 200g", 55, 60, 5, 150),
        ("Chocolate Cookies 150g", 40, 45, 18, 180),
        ("Instant Noodles 70g", 14, 15, 12, 240),
        ("Mixed Namkeen 250g", 70, 80, 12, 120),
    ],
    "Beverages": [
        ("Orange Juice 1L", 99, 110, 12, 120),
        ("Cola 750ml", 40, 45, 28, 180),
        ("Green Tea 25 bags", 140, 160, 5, 365),
        ("Filter Coffee 200g", 185, 200, 5, 270),
        ("Mineral Water 1L", 20, 20, 18, 365),
    ],
    "Health & Medicine": [
        ("Paracetamol 500mg (10 tabs)", 22, 25, 12, 540),
        ("Vitamin C Tablets (30)", 130, 150, 12, 365),
        ("Antiseptic Liquid 100ml", 75, 85, 18, 720),
        ("Cough Syrup 100ml", 88, 95, 12, 420),
        ("ORS Sachet", 21, 22, 12, 365),
    ],
    "Personal Care": [
        ("Herbal Shampoo 180ml", 150, 175, 18, 700),
        ("Sunscreen SPF 50 50g", 320, 360, 18, 540),
        ("Toothpaste 150g", 95, 105, 18, 600),
        ("Hand Wash 250ml", 85, 99, 18, 600),
        ("Face Wash 100ml", 175, 199, 18, 600),
    ],
}


class Command(BaseCommand):
    help = "Seed demo categories, products, batches and users"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing catalog data first")

    @transaction.atomic
    def handle(self, *args, **opts):
        rng = random.Random(42)  # repeatable
        today = timezone.localdate()

        if opts["reset"]:
            ProductBatch.objects.all().delete()
            Product.objects.all().delete()
            Category.objects.all().delete()

        admin, created = User.objects.get_or_create(
            username="admin", defaults={"email": "admin@vetribills.local", "is_staff": True, "is_superuser": True}
        )
        if created:
            admin.set_password("Admin@12345")
            admin.save()
        demo, created = User.objects.get_or_create(
            username="demo", defaults={"email": "demo@vetribills.local", "first_name": "Demo", "last_name": "Customer"}
        )
        if created:
            demo.set_password("Demo@12345")
            demo.save()

        n = 0
        for cat_name, items in CATALOG.items():
            category, _ = Category.objects.get_or_create(name=cat_name)
            for name, price, mrp, tax, shelf in items:
                n += 1
                product, new = Product.objects.get_or_create(
                    sku=f"VB-{n:04d}",
                    defaults=dict(
                        category=category,
                        name=name,
                        description=f"{name} - fresh stock from Vetri Bills. Check the expiry date before use.",
                                                price=Decimal(price),
                        mrp=Decimal(mrp),
                        tax_percent=Decimal(tax),
                        low_stock_threshold=10,
                    ),
                )
                if not new:
                    continue

                # Two batches: an older one and a newer one.
                ProductBatch.objects.create(
                    product=product, batch_no=f"B{n:03d}-A", qty=rng.randint(15, 60),
                    expiry_date=today + timedelta(days=max(3, int(shelf * rng.uniform(0.2, 0.5)))),
                    received_on=today - timedelta(days=30),
                )
                ProductBatch.objects.create(
                    product=product, batch_no=f"B{n:03d}-B", qty=rng.randint(20, 80),
                    expiry_date=today + timedelta(days=shelf),
                    received_on=today - timedelta(days=3),
                )

        # Deliberate demo cases for Day 3 testing.
        self._demo_cases(today)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {Category.objects.count()} categories, {Product.objects.count()} products, "
            f"{ProductBatch.objects.count()} batches."
        ))
        self.stdout.write("Admin login: admin / Admin@12345   Customer login: demo / Demo@12345")

    def _demo_cases(self, today):
        def batch(sku, suffix):
            return ProductBatch.objects.filter(product__sku=sku, batch_no__endswith=suffix).first()

        # Expiring within the 7-day warning window
        for sku, days in (("VB-0001", 2), ("VB-0006", 1), ("VB-0009", 5)):
            b = batch(sku, "-A")
            b.expiry_date = today + timedelta(days=days)
            b.save()
        # Already expired batches
        for sku, days in (("VB-0003", 2), ("VB-0010", 1)):
            b = batch(sku, "-A")
            b.expiry_date = today - timedelta(days=days)
            b.save()
        # Low stock products (threshold is 10)
        for sku, qty in (("VB-0012", 4), ("VB-0018", 8), ("VB-0027", 2)):
            for b in ProductBatch.objects.filter(product__sku=sku):
                b.qty = 0
                b.save()
            b = batch(sku, "-B")
            b.qty = qty
            b.save()

        from catalog.management.commands.attach_product_images import attach_images

        attach_images()
