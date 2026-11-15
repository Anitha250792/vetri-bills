"""Run the expiry and low-stock check once: python manage.py check_expiry_stock

Safe to run as often as you like; the same alert is never created twice.
Use it from Windows Task Scheduler, cron, or a hosting provider's cron job.
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from notifications.services import run_daily_checks


class Command(BaseCommand):
    help = "Create alerts for expired / expiring-soon batches and low-stock products"

    def handle(self, *args, **options):
        result = run_daily_checks()
        self.stdout.write(self.style.SUCCESS(
            f"New alerts: {result['expired']} expired, {result['expiring_soon']} expiring within "
            f"{settings.EXPIRY_WARNING_DAYS} days, {result['low_stock']} low stock."
        ))
