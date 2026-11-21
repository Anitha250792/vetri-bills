from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response

from accounts.permissions import IsShopAdmin

from .admin_serializers import AdminBatchSerializer, AdminProductSerializer
from .models import Product, ProductBatch


class AdminProductListCreateView(generics.ListCreateAPIView):
    """Shop admin: every product (also hidden ones), and add a new product with its first stock."""

    permission_classes = [IsShopAdmin]
    serializer_class = AdminProductSerializer
    pagination_class = None

    def get_queryset(self):
        qs = Product.objects.select_related("category").order_by("name")
        q = self.request.query_params.get("search", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q))
        if self.request.query_params.get("is_active") in ("0", "1"):
            qs = qs.filter(is_active=self.request.query_params["is_active"] == "1")
        return qs


class AdminProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsShopAdmin]
    serializer_class = AdminProductSerializer
    queryset = Product.objects.select_related("category")

    def destroy(self, request, *args, **kwargs):
        # Past bills refer to the product, so "delete" hides it from the shop instead.
        product = self.get_object()
        product.is_active = False
        product.save(update_fields=["is_active", "updated_at"])
        return Response(AdminProductSerializer(product, context={"request": request}).data)


class AdminBatchListCreateView(generics.ListCreateAPIView):
    """Stock deliveries for one product, including expired ones. POST adds new stock."""

    permission_classes = [IsShopAdmin]
    serializer_class = AdminBatchSerializer
    pagination_class = None

    def get_product(self):
        return get_object_or_404(Product, pk=self.kwargs["pk"])

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ProductBatch.objects.none()
        return ProductBatch.objects.filter(product_id=self.kwargs["pk"]).order_by("expiry_date")

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        if not getattr(self, "swagger_fake_view", False):
            ctx["product"] = self.get_product()
        return ctx

    def perform_create(self, serializer):
        serializer.save(product=self.get_product())


class AdminBatchDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsShopAdmin]
    serializer_class = AdminBatchSerializer
    queryset = ProductBatch.objects.select_related("product")
