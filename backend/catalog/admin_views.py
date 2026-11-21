import io

from django.db.models import Q
from drf_spectacular.utils import extend_schema
from PIL import Image, ImageOps
from rest_framework.parsers import MultiPartParser
from rest_framework.views import APIView
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
        qs = Product.objects.select_related("category").defer("image_data").order_by("name")
        q = self.request.query_params.get("search", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q))
        if self.request.query_params.get("is_active") in ("0", "1"):
            qs = qs.filter(is_active=self.request.query_params["is_active"] == "1")
        return qs


class AdminProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsShopAdmin]
    serializer_class = AdminProductSerializer
    queryset = Product.objects.select_related("category").defer("image_data")

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


class AdminProductImageView(APIView):
    """POST a picture (multipart field "image") from the phone or computer. DELETE removes it."""

    permission_classes = [IsShopAdmin]
    parser_classes = [MultiPartParser]

    @extend_schema(request={"multipart/form-data": {"type": "object", "properties": {"image": {"type": "string", "format": "binary"}}}},
                   responses=AdminProductSerializer)
    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        upload = request.FILES.get("image")
        if not upload:
            return Response({"image": "Choose a picture to upload."}, status=status.HTTP_400_BAD_REQUEST)
        if upload.size > 8 * 1024 * 1024:
            return Response({"image": "Picture is too large (max 8 MB)."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            img = Image.open(upload)
            img = ImageOps.exif_transpose(img).convert("RGB")
        except Exception:  # noqa: BLE001 - anything unreadable is simply "not a picture"
            return Response({"image": "That file is not a valid picture."}, status=status.HTTP_400_BAD_REQUEST)
        img.thumbnail((800, 800))  # keeps the database small and the shop fast
        out = io.BytesIO()
        img.save(out, "JPEG", quality=85, optimize=True)
        product.image_data = out.getvalue()
        product.image_version += 1
        product.image_url = ""
        product.save(update_fields=["image_data", "image_version", "image_url", "updated_at"])
        return Response(AdminProductSerializer(product, context={"request": request}).data)

    @extend_schema(responses=AdminProductSerializer)
    def delete(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        product.image_data = None
        product.image_version = 0
        product.save(update_fields=["image_data", "image_version", "updated_at"])
        return Response(AdminProductSerializer(product, context={"request": request}).data)
