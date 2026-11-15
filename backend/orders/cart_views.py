from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Product

from .models import Cart, CartItem, Wishlist
from .serializers import (
    CartAddSerializer,
    CartSerializer,
    CartUpdateSerializer,
    WishlistItemSerializer,
    WishlistToggleSerializer,
)


def _cart_response(request, http_status=status.HTTP_200_OK):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart = Cart.objects.prefetch_related("items__product__category").get(pk=cart.pk)
    return Response(CartSerializer(cart, context={"request": request}).data, status=http_status)


def _check_stock(product, quantity):
    if quantity > product.stock_qty:
        return Response(
            {"detail": f"Only {product.stock_qty} of '{product.name}' in stock.", "available": product.stock_qty},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return None


class CartView(APIView):
    """GET the cart, DELETE to empty it."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CartSerializer

    def get(self, request):
        return _cart_response(request)

    def delete(self, request):
        CartItem.objects.filter(cart__user=request.user).delete()
        return _cart_response(request)


class CartAddView(APIView):
    """POST {product_id, quantity}: adds to the cart (quantities add up)."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CartAddSerializer

    def post(self, request):
        data = CartAddSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        product = get_object_or_404(Product, pk=data.validated_data["product_id"], is_active=True)
        cart, _ = Cart.objects.get_or_create(user=request.user)
        item = CartItem.objects.filter(cart=cart, product=product).first()
        new_qty = (item.quantity if item else 0) + data.validated_data["quantity"]
        error = _check_stock(product, new_qty)
        if error:
            return error
        if item:
            item.quantity = new_qty
            item.save()
        else:
            CartItem.objects.create(cart=cart, product=product, quantity=new_qty)
        return _cart_response(request, status.HTTP_201_CREATED)


class CartItemView(APIView):
    """PATCH {quantity} sets the quantity, DELETE removes the product from the cart."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CartUpdateSerializer

    def _item(self, request, product_id):
        return get_object_or_404(CartItem, cart__user=request.user, product_id=product_id)

    def patch(self, request, product_id):
        item = self._item(request, product_id)
        data = CartUpdateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        error = _check_stock(item.product, data.validated_data["quantity"])
        if error:
            return error
        item.quantity = data.validated_data["quantity"]
        item.save()
        return _cart_response(request)

    def delete(self, request, product_id):
        self._item(request, product_id).delete()
        return _cart_response(request)


class WishlistView(generics.ListAPIView):
    serializer_class = WishlistItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user).select_related("product__category")


class WishlistToggleView(APIView):
    """POST {product_id}: adds the product to the wishlist, or removes it if already there."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WishlistToggleSerializer

    def post(self, request):
        data = WishlistToggleSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        product = get_object_or_404(Product, pk=data.validated_data["product_id"], is_active=True)
        entry, created = Wishlist.objects.get_or_create(user=request.user, product=product)
        if not created:
            entry.delete()
        return Response({"product_id": product.pk, "wishlisted": created})
