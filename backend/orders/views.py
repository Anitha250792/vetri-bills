from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.core.files.base import ContentFile
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .bill_pdf import build_bill_pdf
from .models import Bill, Order, Payment
from .serializers import (
    BillSerializer,
    CheckoutSerializer,
    MockPaySerializer,
    OrderSerializer,
    PaymentVerifySerializer,
)


class CheckoutView(APIView):
    """POST {shipping_address?}: turns the cart into an order and starts the payment."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CheckoutSerializer

    def post(self, request):
        data = CheckoutSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            order = services.create_order_from_cart(request.user, data.validated_data.get("shipping_address", ""))
            payment = services.create_payment(order)
        except services.CheckoutError as exc:
            return Response({"detail": exc.message, "items": exc.details}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"order": OrderSerializer(order, context={"request": request}).data,
             "payment": services.payment_payload(payment)},
            status=status.HTTP_201_CREATED,
        )


class PaymentVerifyView(APIView):
    """POST the three Razorpay values after the customer pays. Signature is checked here, on the server."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PaymentVerifySerializer

    def post(self, request):
        data = PaymentVerifySerializer(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        payment = get_object_or_404(
            Payment, provider_order_id=v["razorpay_order_id"], order__user=request.user
        )
        if not services.verify_signature(v["razorpay_order_id"], v["razorpay_payment_id"], v["razorpay_signature"]):
            payment.status = "failed"
            payment.save(update_fields=["status"])
            return Response({"detail": "Payment verification failed."}, status=status.HTTP_400_BAD_REQUEST)

        order = services.complete_payment(payment, v["razorpay_payment_id"], v["razorpay_signature"])
        if order.status == Order.Status.FAILED:
            return Response(
                {"detail": "Some items sold out while you were paying. Your payment will be refunded."},
                status=status.HTTP_409_CONFLICT,
            )
        bill = services.create_bill(order)
        services.clear_cart(request.user)
        order = Order.objects.get(pk=order.pk)
        return Response(
            {"order": OrderSerializer(order, context={"request": request}).data,
             "bill": BillSerializer(bill, context={"request": request}).data}
        )


class MockPayView(APIView):
    """Development only (MOCK_PAYMENTS=1): returns the values Razorpay would send after a payment."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MockPaySerializer

    def post(self, request):
        if not settings.MOCK_PAYMENTS:
            raise Http404
        data = MockPaySerializer(data=request.data)
        data.is_valid(raise_exception=True)
        payment = get_object_or_404(
            Payment, provider_order_id=data.validated_data["razorpay_order_id"], order__user=request.user
        )
        import secrets

        payment_id = f"pay_mock_{secrets.token_hex(6)}"
        return Response({
            "razorpay_order_id": payment.provider_order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": services.expected_signature(payment.provider_order_id, payment_id),
        })


class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Order.objects.filter(user=self.request.user)
            .exclude(status=Order.Status.CANCELLED)
            .prefetch_related("items")
        )


class OrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related("items")


class BillListView(generics.ListAPIView):
    serializer_class = BillSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Bill.objects.filter(order__user=self.request.user).select_related("order")


class BillDownloadView(APIView):
    """GET the bill PDF. Same file for the mobile app and the website."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={(200, "application/pdf"): OpenApiTypes.BINARY})
    def get(self, request, pk):
        bill = get_object_or_404(Bill.objects.select_related("order__user"), pk=pk, order__user=request.user)
        if not bill.pdf_file or not bill.pdf_file.storage.exists(bill.pdf_file.name):
            bill.pdf_file.save(f"{bill.bill_no}.pdf", ContentFile(build_bill_pdf(bill)), save=True)
        return FileResponse(
            bill.pdf_file.open("rb"), as_attachment=True, filename=f"{bill.bill_no}.pdf",
            content_type="application/pdf",
        )
