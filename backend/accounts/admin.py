from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import DeviceToken, User


@admin.register(User)
class VetriUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "phone", "is_active")
    list_filter = ("role", "is_active", "is_staff")
    fieldsets = UserAdmin.fieldsets + (("Vetri Bills", {"fields": ("role", "phone", "address")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Vetri Bills", {"fields": ("email", "role", "phone")}),
    )


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "platform", "created_at")
