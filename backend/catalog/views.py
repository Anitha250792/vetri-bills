from django.http import Http404, HttpResponse
from django.db.models import Count, Q
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView
from django_filters import rest_framework as filters
from rest_framework import generics, permissions

from .models import Category, Product
from .serializers import CategorySerializer, ProductDetailSerializer, ProductListSerializer


class ProductFilter(filters.FilterSet):
    category = filters.CharFilter(field_name="category__slug")
    min_price = filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="price", lookup_expr="lte")
    in_stock = filters.BooleanFilter(method="filter_in_stock")

    class Meta:
        model = Product
        fields = ["category", "min_price", "max_price", "in_stock"]

    def filter_in_stock(self, queryset, name, value):
        return queryset.filter(stock_qty__gt=0) if value else queryset.filter(stock_qty=0)


class CategoryListView(generics.ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        return Category.objects.annotate(
            product_count=Count("products", filter=Q(products__is_active=True))
        )


class ProductListView(generics.ListAPIView):
    """GET /api/products/?search=milk&category=dairy&min_price=10&ordering=-price&page=2"""

    serializer_class = ProductListSerializer
    permission_classes = [permissions.AllowAny]
    filterset_class = ProductFilter
    search_fields = ["name", "description", "sku", "category__name"]
    ordering_fields = ["price", "name", "created_at"]

    def get_queryset(self):
        return Product.objects.filter(is_active=True).select_related("category").defer("image_data")


class ProductDetailView(generics.RetrieveAPIView):
    serializer_class = ProductDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "pk"

    def get_queryset(self):
        return Product.objects.filter(is_active=True).select_related("category").defer("image_data")


class ProductImageView(APIView):
    """GET /api/products/<id>/image/ : the picture an admin uploaded (cached by ?v=version)."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(exclude=True)
    def get(self, request, pk):
        product = Product.objects.filter(pk=pk).only("image_data", "image_version").first()
        if not product or not product.image_data:
            raise Http404
        response = HttpResponse(bytes(product.image_data), content_type="image/jpeg")
        response["Cache-Control"] = "public, max-age=31536000, immutable"
        return response
