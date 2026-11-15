#!/usr/bin/env bash
# Runs on every deploy (Render "Build Command": ./build.sh)
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input
# Demo data only the first time (skipped when products already exist)
python - <<'PY'
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from catalog.models import Product
from django.core.management import call_command
if os.getenv("SEED_DEMO", "0") == "1" and not Product.objects.exists():
    call_command("seed_data")
PY
python manage.py attach_product_images
