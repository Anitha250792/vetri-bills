"""Download a real photo for each product from Wikipedia / Wikimedia Commons (free, no key).

    python manage.py fetch_product_images            # products without a picture, or with a drawing
    python manage.py fetch_product_images --force    # replace every picture

Needs internet on the machine that runs it. Anything that cannot be fetched keeps the bundled picture.
You can always replace a picture by hand in Django admin > Products > Image.
"""
import io
import json
import urllib.parse
import urllib.request

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image

from catalog.management.commands.attach_product_images import attach_images
from catalog.models import Product

API = "https://en.wikipedia.org/w/api.php"
UA = {"User-Agent": "VetriBills/1.0 (student project; contact: admin@vetribills.local)"}

# product name -> Wikipedia article titles to try, best first
TITLES = {
    "Full Cream Milk 1L": ["Milk"],
    "Curd 400g": ["Dahi", "Curd", "Yogurt"],
    "Paneer 200g": ["Paneer"],
    "Salted Butter 100g": ["Butter"],
    "Farm Eggs (12 pack)": ["Chicken egg", "Egg as food", "Egg"],
    "Sandwich Bread 400g": ["Sliced bread", "Sandwich bread", "Bread"],
    "Whole Wheat Bread 400g": ["Whole-wheat bread", "Whole wheat bread", "Bread"],
    "Chocolate Muffin": ["Muffin", "Chocolate chip muffin"],
    "Veg Puff": ["Puff pastry", "Samosa"],
    "Fruit Cake 250g": ["Fruitcake", "Fruit cake"],
    "Potato Chips 90g": ["Potato chip", "Potato chips"],
    "Salted Peanuts 200g": ["Peanut", "Roasted peanuts"],
    "Chocolate Cookies 150g": ["Chocolate chip cookie", "Cookie"],
    "Instant Noodles 70g": ["Instant noodle", "Instant noodles"],
    "Mixed Namkeen 250g": ["Bombay mix", "Chivda", "Namkeen"],
    "Orange Juice 1L": ["Orange juice"],
    "Cola 750ml": ["Cola", "Coca-Cola"],
    "Green Tea 25 bags": ["Green tea", "Tea bag"],
    "Filter Coffee 200g": ["Indian filter coffee", "Filter coffee", "Coffee"],
    "Mineral Water 1L": ["Bottled water", "Mineral water"],
    "Paracetamol 500mg (10 tabs)": ["Paracetamol", "Acetaminophen"],
    "Vitamin C Tablets (30)": ["Vitamin C", "Ascorbic acid"],
    "Antiseptic Liquid 100ml": ["Antiseptic", "Dettol"],
    "Cough Syrup 100ml": ["Cough medicine", "Cough syrup"],
    "ORS Sachet": ["Oral rehydration therapy", "Oral rehydration solution"],
    "Herbal Shampoo 180ml": ["Shampoo"],
    "Sunscreen SPF 50 50g": ["Sunscreen"],
    "Toothpaste 150g": ["Toothpaste"],
    "Hand Wash 250ml": ["Liquid hand soap", "Hand washing", "Soap"],
    "Face Wash 100ml": ["Facial cleanser", "Cleanser", "Face wash"],
}
BAD = ("logo", ".svg", "flag", "map", "icon", "symbol", "diagram", "structure")


def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
        return r.read()


def find_photo_url(title):
    qs = urllib.parse.urlencode({
        "action": "query", "format": "json", "prop": "pageimages", "piprop": "thumbnail",
        "pithumbsize": 700, "redirects": 1, "titles": title,
    })
    pages = json.loads(_get(f"{API}?{qs}"))["query"]["pages"]
    for page in pages.values():
        src = page.get("thumbnail", {}).get("source", "")
        if src and not any(bad in src.lower() for bad in BAD):
            return src
    return None


def square_jpeg(raw):
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    side = min(img.size)
    left, top = (img.width - side) // 2, (img.height - side) // 2
    img = img.crop((left, top, left + side, top + side)).resize((600, 600), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, "JPEG", quality=88)
    return out.getvalue()


class Command(BaseCommand):
    help = "Download real product photos (Wikipedia) and attach them to products"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Replace pictures that are already real photos")

    def handle(self, *args, **opts):
        attach_images()  # make sure everything has at least the bundled picture
        got = 0
        for product in Product.objects.all():
            if product.image and product.image.name.endswith(".jpg") and not opts["force"]:
                continue  # already a real photo
            for title in TITLES.get(product.name, [product.name]):
                try:
                    url = find_photo_url(title)
                    if not url:
                        continue
                    data = square_jpeg(_get(url))
                except Exception as exc:  # noqa: BLE001 - network/image problems just try the next title
                    self.stdout.write(f"  ! {title}: {exc}")
                    continue
                product.image.save(f"{product.sku}.jpg", ContentFile(data), save=False)
                product.image_url = ""
                product.save(update_fields=["image", "image_url"])
                self.stdout.write(self.style.SUCCESS(f"  ok  {product.name}  <-  {title}"))
                got += 1
                break
            else:
                self.stdout.write(self.style.WARNING(f"  --  {product.name}: kept bundled picture"))
        self.stdout.write(self.style.SUCCESS(f"Real photos for {got} products."))
