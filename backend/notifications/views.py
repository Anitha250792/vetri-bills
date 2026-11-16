from datetime import timedelta

from django.conf import settings
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsShopAdmin
from catalog.models import Product, ProductBatch

from . import services
from .models import Notification
from .serializers import BatchReportSerializer, LowStockReportSerializer, NotificationSerializer


class NotificationListView(generics.ListAPIView):
    """GET /api/notifications/?is_read=false&type=expiry_soon  (newest first)"""

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["type", "is_read"]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class UnreadCountView(APIView):
    """For the bell badge in the app."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        return Response({"unread": Notification.objects.filter(user=request.user, is_read=False).count()})


class MarkReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=None, responses={200: NotificationSerializer})
    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read"])
        return Response(NotificationSerializer(notification).data)


class MarkAllReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=None, responses={200: OpenApiTypes.OBJECT})
    def post(self, request):
        updated = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"updated": updated})


class ExpiryStockReportView(APIView):
    """Admin only: what has expired, what expires soon, and what is running low."""

    permission_classes = [IsShopAdmin]

    @extend_schema(
        parameters=[OpenApiParameter("days", int, description="Look-ahead window (default 7, max 365)")],
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request):
        try:
            days = int(request.query_params.get("days", settings.EXPIRY_WARNING_DAYS))
            if not 0 <= days <= 365:
                raise ValueError
        except ValueError:
            return Response({"detail": "days must be a whole number from 0 to 365."}, status=400)

        services.refresh_stock()  # so expired batches are no longer counted as stock
        today = timezone.localdate()
        batches = ProductBatch.objects.filter(qty__gt=0).select_related("product")
        expired = batches.filter(expiry_date__lt=today).order_by("expiry_date")
        soon = batches.filter(expiry_date__gte=today, expiry_date__lte=today + timedelta(days=days)).order_by("expiry_date")
        low = (Product.objects.filter(is_active=True, stock_qty__lte=F("low_stock_threshold"))
               .select_related("category").order_by("stock_qty", "name"))
        return Response({
            "as_of": today,
            "warning_days": days,
            "summary": {"expired": expired.count(), "expiring_soon": soon.count(), "low_stock": low.count()},
            "expired": BatchReportSerializer(expired, many=True).data,
            "expiring_soon": BatchReportSerializer(soon, many=True).data,
            "low_stock": LowStockReportSerializer(low, many=True).data,
        })


class DailyCheckCronView(APIView):
    """Called once a day by Vercel Cron (which sends `Authorization: Bearer $CRON_SECRET`)."""

    authentication_classes = []
    permission_classes = []

    @extend_schema(exclude=True)
    def get(self, request):
        import os

        secret = os.getenv("CRON_SECRET", "")
        if not secret or request.headers.get("Authorization") != f"Bearer {secret}":
            return Response({"detail": "Forbidden"}, status=403)
        from .services import run_daily_checks

        return Response({"detail": "ok", "result": str(run_daily_checks())})
