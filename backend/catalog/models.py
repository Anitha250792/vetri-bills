from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from django.utils.text import slugify

from .signals import stock_changed


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    image = models.ImageField(upload_to="categories/", blank=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    sku = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="products/", blank=True)
    image_url = models.URLField(blank=True, help_text="Use instead of an upload (e.g. seed data)")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    mrp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    stock_qty = models.PositiveIntegerField(
        default=0, help_text="Kept in sync with the sum of its active batches"
    )
    low_stock_threshold = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "product"
            slug, n = base, 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                n += 1
                slug = f"{base}-{n}"
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def is_low_stock(self):
        return self.stock_qty <= self.low_stock_threshold

    @property
    def nearest_expiry(self):
        batch = (
            self.batches.filter(qty__gt=0, expiry_date__gte=timezone.localdate())
            .order_by("expiry_date")
            .first()
        )
        return batch.expiry_date if batch else None

    def recalc_stock(self):
        """Stock = quantity in batches that have not expired yet."""
        total = (
            self.batches.filter(expiry_date__gte=timezone.localdate()).aggregate(t=Sum("qty"))["t"]
            or 0
        )
        # Products without any batch keep the manually entered stock.
        if self.batches.exists():
            self.stock_qty = total
            self.save(update_fields=["stock_qty", "updated_at"])

    def __str__(self):
        return self.name


class ProductBatch(models.Model):
    """One delivery of a product. Expiry is tracked per batch."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="batches")
    batch_no = models.CharField(max_length=50)
    qty = models.PositiveIntegerField()
    expiry_date = models.DateField()
    received_on = models.DateField(default=timezone.localdate)

    class Meta:
        verbose_name_plural = "product batches"
        ordering = ["expiry_date"]
        unique_together = [("product", "batch_no")]

    @property
    def days_to_expiry(self):
        return (self.expiry_date - timezone.localdate()).days

    @property
    def is_expired(self):
        return self.days_to_expiry < 0

    @property
    def is_expiring_soon(self):
        return 0 <= self.days_to_expiry <= settings.EXPIRY_WARNING_DAYS

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.product.recalc_stock()
        stock_changed.send(sender=ProductBatch, product=self.product, batch=self)

    def delete(self, *args, **kwargs):
        product = self.product
        super().delete(*args, **kwargs)
        product.recalc_stock()
        stock_changed.send(sender=ProductBatch, product=product, batch=None)

    def __str__(self):
        return f"{self.product.name} / {self.batch_no} (exp {self.expiry_date})"
