from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Type(models.TextChoices):
        EXPIRY_SOON = "expiry_soon", "Expiring soon"
        EXPIRED = "expired", "Expired"
        LOW_STOCK = "low_stock", "Low stock"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=20, choices=Type.choices)
    message = models.CharField(max_length=300)
    product = models.ForeignKey("catalog.Product", null=True, blank=True, on_delete=models.CASCADE)
    batch = models.ForeignKey("catalog.ProductBatch", null=True, blank=True, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=False)
    # Low-stock alerts are resolved once the product is restocked, so it can alert again later.
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.type}] {self.message[:50]}"
