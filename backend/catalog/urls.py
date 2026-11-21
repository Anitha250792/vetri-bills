from django.urls import path

from . import admin_views, views

urlpatterns = [
    path("categories/", views.CategoryListView.as_view(), name="category-list"),
    path("products/", views.ProductListView.as_view(), name="product-list"),
    path("products/<int:pk>/", views.ProductDetailView.as_view(), name="product-detail"),
    # shop admin (in-app product and stock management)
    path("admin/products/", admin_views.AdminProductListCreateView.as_view(), name="admin-product-list"),
    path("admin/products/<int:pk>/", admin_views.AdminProductDetailView.as_view(), name="admin-product-detail"),
    path("admin/products/<int:pk>/batches/", admin_views.AdminBatchListCreateView.as_view(), name="admin-batch-list"),
    path("admin/batches/<int:pk>/", admin_views.AdminBatchDetailView.as_view(), name="admin-batch-detail"),
]
