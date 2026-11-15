from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    name = "notifications"

    def ready(self):
        from catalog.signals import stock_changed

        from .services import on_stock_changed

        # Admin edits and sales call this, so alerts appear straight away, not only at the daily run.
        stock_changed.connect(on_stock_changed, dispatch_uid="notifications.on_stock_changed")
