from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from catalog.models import Product

IMAGES = Path(settings.BASE_DIR) / "assets" / "product_images"


def attach_images(force=False):
    """Give every product the picture that matches it (assets/product_images/<sku>.png)."""
    done = 0
    for product in Product.objects.all():
        src = IMAGES / f"{product.sku}.png"
        if not src.exists() or (product.image and not force):
            continue
        with src.open("rb") as fh:
            product.image.save(f"{product.sku}.png", File(fh), save=False)
        product.image_url = ""
        product.save(update_fields=["image", "image_url"])
        done += 1
    return done


class Command(BaseCommand):
    help = "Attach the bundled product pictures to products (use --force to replace existing ones)"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **opts):
        self.stdout.write(self.style.SUCCESS(f"Pictures attached to {attach_images(opts['force'])} products."))
