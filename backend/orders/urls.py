from django.urls import path

from . import cart_views, views

urlpatterns = [
    # cart
    path("cart/", cart_views.CartView.as_view(), name="cart"),
    path("cart/items/", cart_views.CartAddView.as_view(), name="cart-add"),
    path("cart/items/<int:product_id>/", cart_views.CartItemView.as_view(), name="cart-item"),
    # wishlist
    path("wishlist/", cart_views.WishlistView.as_view(), name="wishlist"),
    path("wishlist/toggle/", cart_views.WishlistToggleView.as_view(), name="wishlist-toggle"),
    # checkout + payment
    path("checkout/", views.CheckoutView.as_view(), name="checkout"),
    path("payments/verify/", views.PaymentVerifyView.as_view(), name="payment-verify"),
    path("payments/mock-pay/", views.MockPayView.as_view(), name="payment-mock"),
    # orders + bills
    path("orders/", views.OrderListView.as_view(), name="order-list"),
    path("orders/<int:pk>/", views.OrderDetailView.as_view(), name="order-detail"),
    path("bills/", views.BillListView.as_view(), name="bill-list"),
    path("bills/<int:pk>/download/", views.BillDownloadView.as_view(), name="bill-download"),
]
