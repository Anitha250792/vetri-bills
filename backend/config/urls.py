from django.conf import settings
from django.contrib import admin
from django.http import Http404
from django.urls import include, path, re_path
from django.views.static import serve
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

def product_image(request, path):
    """Product pictures: uploaded ones first, then the pictures bundled with the code."""
    for root in (settings.MEDIA_ROOT / "products", settings.BASE_DIR / "media" / "products",
                 settings.BASE_DIR / "assets" / "product_images"):
        if (root / path).is_file():
            return serve(request, path, document_root=root)
    raise Http404


admin.site.site_header = "Vetri Bills Admin"
admin.site.site_title = "Vetri Bills"
admin.site.index_title = "Shop dashboard"

urlpatterns = [
    path("", RedirectView.as_view(url="/api/docs/", permanent=False)),
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("catalog.urls")),
    path("api/", include("orders.urls")),
    path("api/", include("notifications.urls")),
    # API docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    re_path(r"^media/products/(?P<path>.*)$", product_image),
    # Other uploads. Fine for a small shop; use S3/Cloudinary storage if it grows.
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
