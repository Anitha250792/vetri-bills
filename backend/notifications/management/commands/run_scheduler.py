"""Keeps running and does the daily check at SCHEDULE_HOUR:SCHEDULE_MINUTE (default 08:00).

    python manage.py run_scheduler          # wait for the daily time
    python manage.py run_scheduler --now    # also run one check immediately

Run it next to the web server (a second terminal, or a background worker on your host).
"""
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from django.conf import settings
from django.core.management.base import BaseCommand

from notifications.services import run_daily_checks


def job():
    result = run_daily_checks()
    print(f"[check] new alerts: {result}", flush=True)


class Command(BaseCommand):
    help = "Run the expiry / low-stock check every day"

    def add_arguments(self, parser):
        parser.add_argument("--now", action="store_true", help="Also run one check right away")

    def handle(self, *args, **options):
        if options["now"]:
            job()
        scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)
        scheduler.add_job(
            job,
            CronTrigger(hour=settings.SCHEDULE_HOUR, minute=settings.SCHEDULE_MINUTE),
            id="daily-expiry-stock-check", max_instances=1, coalesce=True, misfire_grace_time=3600,
        )
        self.stdout.write(self.style.SUCCESS(
            f"Scheduler running. Daily check at {settings.SCHEDULE_HOUR:02d}:{settings.SCHEDULE_MINUTE:02d} "
            f"({settings.TIME_ZONE}). Press Ctrl+C to stop."
        ))
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            self.stdout.write("Scheduler stopped.")
