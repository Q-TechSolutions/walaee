"""
نقاط الاشتراك والفوترة.

كلها للمالك: الباقة والفواتير ورصيد الرسائل أرقام مالية تخص صاحب
التعاقد لا مدير الفرع.
"""

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.pos.permissions import IsOwner, get_staff_user

from . import services
from .gateways import get_gateway
from .models import Invoice, MessageCredit, Subscription


class SubscriptionSerializer(serializers.ModelSerializer):
    plan_label = serializers.CharField(source="get_plan_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    limits = serializers.DictField(read_only=True)

    class Meta:
        model = Subscription
        fields = (
            "id",
            "plan",
            "plan_label",
            "status",
            "status_label",
            "mrr",
            "current_period_start",
            "current_period_end",
            "limits",
        )
        read_only_fields = fields


class InvoiceSerializer(serializers.ModelSerializer):
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Invoice
        fields = (
            "id",
            "number",
            "amount",
            "tax_amount",
            "total",
            "status",
            "status_label",
            "period_start",
            "period_end",
            "issued_at",
            "paid_at",
        )
        read_only_fields = fields


class CreditSerializer(serializers.ModelSerializer):
    reason_label = serializers.CharField(source="get_reason_display", read_only=True)

    class Meta:
        model = MessageCredit
        fields = ("id", "delta", "reason", "reason_label", "balance_after", "note", "created_at")
        read_only_fields = fields


class SubscriptionView(APIView):
    permission_classes = [IsOwner]

    @extend_schema(responses=SubscriptionSerializer, summary="الاشتراك وحدود الباقة")
    def get(self, request):
        staff = get_staff_user(request)
        organization = staff.branch.brand.organization
        subscription = services.get_subscription(organization)

        return Response(
            {
                **SubscriptionSerializer(subscription).data,
                "limits": {
                    key: (str(value) if value is not None else None)
                    for key, value in subscription.limits.items()
                },
                "usage": _usage(organization),
                "message_balance": services.wallet_balance(organization),
            }
        )


def _usage(organization) -> dict:
    """
    الاستهلاك الفعلي مقابل الحدود.

    يُعرض بجوار الحدود لا في شاشة منفصلة: التاجر يحتاج أن يرى أنه
    اقترب من الحد قبل أن يصطدم برسالة رفض وهو يضيف فرعًا.
    """
    from apps.accounts.models import Customer
    from apps.loyalty.models import LoyaltyProgram
    from apps.tenancy.models import Branch, StaffUser, Terminal

    brands = organization.brands.all()

    return {
        "branches": Branch.objects.filter(brand__in=brands).count(),
        "terminals": Terminal.objects.filter(branch__brand__in=brands).count(),
        "staff": StaffUser.objects.filter(branch__brand__in=brands).count(),
        "programs": LoyaltyProgram.objects.filter(brand__in=brands).count(),
        "customers": Customer.objects.filter(memberships__brand__in=brands, deleted_at__isnull=True)
        .distinct()
        .count(),
    }


class InvoiceListView(APIView):
    permission_classes = [IsOwner]

    @extend_schema(responses=InvoiceSerializer(many=True), summary="فواتير الاشتراك")
    def get(self, request):
        staff = get_staff_user(request)
        subscription = services.get_subscription(staff.branch.brand.organization)

        invoices = Invoice.objects.filter(subscription=subscription).order_by("-created_at")[:50]
        return Response(InvoiceSerializer(invoices, many=True).data)


class InvoicePaymentView(APIView):
    permission_classes = [IsOwner]

    @extend_schema(request=None, responses={200: None}, summary="تعليمات سداد فاتورة")
    def get(self, request, pk):
        staff = get_staff_user(request)
        subscription = services.get_subscription(staff.branch.brand.organization)

        invoice = Invoice.objects.get(pk=pk, subscription=subscription)
        intent = get_gateway().create_intent(invoice=invoice)

        return Response(
            {
                "invoice": InvoiceSerializer(invoice).data,
                "reference": intent.reference,
                "amount": str(intent.amount),
                "instructions": intent.instructions,
                "checkout_url": intent.checkout_url,
            }
        )


class MessageWalletView(APIView):
    permission_classes = [IsOwner]

    @extend_schema(responses={200: None}, summary="رصيد الرسائل وحركاته")
    def get(self, request):
        staff = get_staff_user(request)
        organization = staff.branch.brand.organization

        credits = MessageCredit.objects.filter(organization=organization).order_by("-created_at")[
            :50
        ]

        return Response(
            {
                "balance": services.wallet_balance(organization),
                "history": CreditSerializer(credits, many=True).data,
            }
        )
