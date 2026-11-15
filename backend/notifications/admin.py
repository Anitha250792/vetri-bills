from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("type", "message", "user", "is_read", "resolved", "created_at")
    list_filter = ("type", "is_read", "resolved")
