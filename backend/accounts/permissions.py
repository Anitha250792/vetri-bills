from rest_framework.permissions import BasePermission


class IsShopAdmin(BasePermission):
    """Only users with the admin role (the shop owner / staff)."""

    message = "Only shop admins can do this."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == "admin")
