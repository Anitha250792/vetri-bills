from datetime import date

from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Category, Product, ProductBatch
from .serializers import product_image_url
from .signals import stock_changed


def _next_batch_no(product):
    return f"B{timezone.localdate():%y%m%d}-{product.batches.count() + 1}"


class AdminBatchSerializer(serializers.ModelSerializer):
    days_to_expiry = serializers.IntegerField(read_only=True)
    batch_no = serializers.CharField(max_length=50, required=False, allow_blank=True)

    class Meta:
        model = ProductBatch
        fields = ("id", "batch_no", "qty", "expiry_date", "received_on", "days_to_expiry")
        read_only_fields = ("received_on",)
        validators = []  # uniqueness is checked below with a friendlier message

    def validate_qty(self, value):
        if value < 0:
            raise serializers.ValidationError("Quantity cannot be negative.")
        return value

    def validate(self, attrs):
        product = self.context["product"] if "product" in self.context else self.instance.product
        batch_no = (attrs.get("batch_no") or (self.instance.batch_no if self.instance else "")).strip()
        if not batch_no:
            batch_no = _next_batch_no(product)
        clash = product.batches.filter(batch_no=batch_no)
        if self.instance:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError({"batch_no": f"Batch {batch_no} already exists for this product."})
        attrs["batch_no"] = batch_no
        return attrs


class InitialBatchSerializer(serializers.Serializer):
    batch_no = serializers.CharField(max_length=50, required=False, allow_blank=True)
    qty = serializers.IntegerField(min_value=0)
    expiry_date = serializers.DateField()


class AdminProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    sku = serializers.CharField(max_length=50, required=False, allow_blank=True)
    batch_count = serializers.SerializerMethodField()
    nearest_expiry = serializers.DateField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    image = serializers.SerializerMethodField()
    # Create only: first delivery, so a new product starts with stock and an expiry date.
    initial_batch = InitialBatchSerializer(write_only=True, required=False)

    class Meta:
        model = Product
        fields = (
            "id", "name", "sku", "category", "category_name", "description", "image_url", "image",
            "price", "mrp", "tax_percent", "low_stock_threshold", "is_active", "stock_qty",
            "is_low_stock", "nearest_expiry", "batch_count", "initial_batch",
        )
        read_only_fields = ("stock_qty",)

    @extend_schema_field(serializers.IntegerField())
    def get_batch_count(self, obj):
        return obj.batches.count()

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_image(self, obj):
        if obj.image_version:
            return product_image_url(obj, self.context.get("request"))
        if obj.image:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return obj.image_url or None

    def validate(self, attrs):
        price, mrp = attrs.get("price"), attrs.get("mrp")
        if price is not None and price <= 0:
            raise serializers.ValidationError({"price": "Price must be more than 0."})
        if price is not None and mrp is not None and mrp < price:
            raise serializers.ValidationError({"mrp": "MRP cannot be lower than the selling price."})
        return attrs

    def validate_sku(self, value):
        value = value.strip()
        if value:
            clash = Product.objects.filter(sku=value)
            if self.instance:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise serializers.ValidationError("This SKU is already used.")
        return value

    @transaction.atomic
    def create(self, validated):
        initial = validated.pop("initial_batch", None)
        if not validated.get("sku"):
            validated["sku"] = f"VB-{(Product.objects.order_by('-id').values_list('id', flat=True).first() or 0) + 1:04d}"
            while Product.objects.filter(sku=validated["sku"]).exists():
                validated["sku"] += "x"
        product = Product.objects.create(**validated)
        if initial:
            batch = ProductBatch(
                product=product, batch_no=(initial.get("batch_no") or "").strip() or "B1",
                qty=initial["qty"], expiry_date=initial["expiry_date"],
            )
            batch.save()  # recalculates stock and raises the expiry / low-stock alerts
        else:
            stock_changed.send(sender=Product, product=product, batch=None)
        return product

    def update(self, instance, validated):
        validated.pop("initial_batch", None)
        was_threshold = instance.low_stock_threshold
        product = super().update(instance, validated)
        if product.low_stock_threshold != was_threshold:
            stock_changed.send(sender=Product, product=product, batch=None)
        return product
