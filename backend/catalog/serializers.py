from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Category, Product, ProductBatch


def product_image_url(product, request=None):
    path = f"/api/products/{product.pk}/image/?v={product.image_version}"
    return request.build_absolute_uri(path) if request else path


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "image", "product_count")


class ProductBatchSerializer(serializers.ModelSerializer):
    days_to_expiry = serializers.IntegerField(read_only=True)

    class Meta:
        model = ProductBatch
        fields = ("id", "batch_no", "qty", "expiry_date", "days_to_expiry")


class _ProductBase(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    image = serializers.SerializerMethodField()
    discount_percent = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()
    is_low_stock = serializers.BooleanField(read_only=True)
    nearest_expiry = serializers.DateField(read_only=True)

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_image(self, obj):
        if obj.image_version:
            return product_image_url(obj, self.context.get("request"))
        if obj.image:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return obj.image_url or None

    @extend_schema_field(serializers.IntegerField())
    def get_discount_percent(self, obj):
        if obj.mrp and obj.mrp > obj.price:
            return int(round((obj.mrp - obj.price) / obj.mrp * 100))
        return 0

    @extend_schema_field(serializers.BooleanField())
    def get_in_stock(self, obj):
        return obj.stock_qty > 0


class ProductListSerializer(_ProductBase):
    """Compact card data for the product grid."""

    class Meta:
        model = Product
        fields = (
            "id", "name", "slug", "category", "category_name", "image", "price", "mrp",
            "discount_percent", "stock_qty", "in_stock", "is_low_stock", "nearest_expiry",
        )


class ProductDetailSerializer(_ProductBase):
    """Full data for the product page, including batches and expiry dates."""

    batches = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id", "name", "slug", "sku", "description", "category", "category_name", "image",
            "price", "mrp", "discount_percent", "tax_percent", "stock_qty", "in_stock",
            "low_stock_threshold", "is_low_stock", "nearest_expiry", "batches",
        )

    @extend_schema_field(ProductBatchSerializer(many=True))
    def get_batches(self, obj):
        # Only batches that can still be sold.
        from django.utils import timezone

        qs = obj.batches.filter(qty__gt=0, expiry_date__gte=timezone.localdate())
        return ProductBatchSerializer(qs, many=True).data
