from django.urls import path

from . import views

urlpatterns = [
    path("notifications/", views.NotificationListView.as_view(), name="notification-list"),
    path("notifications/unread-count/", views.UnreadCountView.as_view(), name="notification-unread"),
    path("notifications/read-all/", views.MarkAllReadView.as_view(), name="notification-read-all"),
    path("notifications/<int:pk>/read/", views.MarkReadView.as_view(), name="notification-read"),
    path("admin/expiry-report/", views.ExpiryStockReportView.as_view(), name="expiry-report"),
]
