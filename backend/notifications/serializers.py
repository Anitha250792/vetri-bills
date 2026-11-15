from rest_framework import serializers

from catalog.models import Product, ProductBatch

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "type", "message", "product", "batch", "is_read", "created_at")
        read_only_fields = fields


class BatchReportSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    sku = serializers.CharField(source="product.sku", read_only=True)
    days_to_expiry = serializers.IntegerField(read_only=True)

    class Meta:
        model = ProductBatch
        fields = ("id", "product_id", "product_name", "sku", "batch_no", "qty", "expiry_date", "days_to_expiry")


class LowStockReportSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Product
        fields = ("id", "name", "sku", "category_name", "stock_qty", "low_stock_threshold")
