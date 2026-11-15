from django.urls import reverse
from rest_framework.test import APITestCase

from .models import User


class AuthTests(APITestCase):
    def register(self, **extra):
        data = {"username": "asha", "email": "Asha@Example.com", "password": "Str0ng!Pass1", **extra}
        return self.client.post(reverse("register"), data)

    def test_register_creates_customer_and_hides_password(self):
        r = self.register()
        self.assertEqual(r.status_code, 201)
        self.assertNotIn("password", r.data)
        user = User.objects.get(username="asha")
        self.assertEqual(user.role, User.Role.CUSTOMER)
        self.assertEqual(user.email, "asha@example.com")

    def test_cannot_self_register_as_admin(self):
        self.register(role="admin", is_staff=True, is_superuser=True)
        user = User.objects.get(username="asha")
        self.assertEqual(user.role, User.Role.CUSTOMER)
        self.assertFalse(user.is_staff)

    def test_duplicate_email_rejected(self):
        self.register()
        r = self.register(username="other")
        self.assertEqual(r.status_code, 400)

    def test_weak_password_rejected(self):
        r = self.register(password="12345678")
        self.assertEqual(r.status_code, 400)

    def test_login_with_username_or_email_returns_tokens_and_profile(self):
        self.register()
        for ident in ("asha", "asha@example.com"):
            r = self.client.post(reverse("login"), {"username": ident, "password": "Str0ng!Pass1"})
            self.assertEqual(r.status_code, 200, ident)
            self.assertIn("access", r.data)
            self.assertIn("refresh", r.data)
            self.assertEqual(r.data["user"]["role"], "customer")

    def test_login_wrong_password(self):
        self.register()
        r = self.client.post(reverse("login"), {"username": "asha", "password": "nope"})
        self.assertEqual(r.status_code, 401)

    def test_profile_requires_auth_and_can_be_updated(self):
        self.assertEqual(self.client.get(reverse("profile")).status_code, 401)
        self.register()
        token = self.client.post(reverse("login"), {"username": "asha", "password": "Str0ng!Pass1"}).data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        r = self.client.patch(reverse("profile"), {"phone": "9876543210", "role": "admin"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["phone"], "9876543210")
        self.assertEqual(r.data["role"], "customer")  # role is read-only

    def test_device_token_saved(self):
        self.register()
        token = self.client.post(reverse("login"), {"username": "asha", "password": "Str0ng!Pass1"}).data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        r = self.client.post(reverse("device-token"), {"token": "ExponentPushToken[abc]", "platform": "android"})
        self.assertEqual(r.status_code, 204)
        self.assertEqual(User.objects.get(username="asha").device_tokens.count(), 1)
