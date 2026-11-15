from decimal import Decimal

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from catalog.serializers import ProductListSerializer

from .models import Bill, Cart, CartItem, Order, OrderItem, Wishlist


# ---------------------------------------------------------------- cart ----
class CartItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ("id", "product", "quantity", "line_total")

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_line_total(self, obj):
        return obj.product.price * obj.quantity


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    item_count = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ("items", "item_count", "total")

    @extend_schema_field(serializers.IntegerField())
    def get_item_count(self, obj):
        return sum(i.quantity for i in obj.items.all())

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_total(self, obj):
        return sum((i.product.price * i.quantity for i in obj.items.all()), Decimal("0"))


class CartAddSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)


class CartUpdateSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)


class WishlistToggleSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()


class WishlistItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)

    class Meta:
        model = Wishlist
        fields = ("id", "product", "added_at")


# -------------------------------------------------------------- orders ----
class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ("id", "product", "product_name", "unit_price", "tax_percent", "quantity", "line_total")


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    bill = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            "id", "status", "subtotal", "tax_total", "total", "shipping_address",
            "created_at", "items", "bill",
        )

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_bill(self, obj):
        bill = getattr(obj, "bill", None)
        return {"id": bill.id, "bill_no": bill.bill_no} if bill else None


class CheckoutSerializer(serializers.Serializer):
    shipping_address = serializers.CharField(required=False, allow_blank=True)


class PaymentVerifySerializer(serializers.Serializer):
    razorpay_order_id = serializers.CharField()
    razorpay_payment_id = serializers.CharField()
    razorpay_signature = serializers.CharField()


class MockPaySerializer(serializers.Serializer):
    razorpay_order_id = serializers.CharField()


class BillSerializer(serializers.ModelSerializer):
    order_id = serializers.IntegerField(read_only=True)
    total = serializers.DecimalField(source="order.total", max_digits=12, decimal_places=2, read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Bill
        fields = ("id", "bill_no", "order_id", "total", "created_at", "download_url")

    @extend_schema_field(serializers.CharField())
    def get_download_url(self, obj):
        request = self.context.get("request")
        path = f"/api/bills/{obj.pk}/download/"
        return request.build_absolute_uri(path) if request else path
