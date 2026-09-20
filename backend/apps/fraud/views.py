"""
مراجعة إشارات الشذوذ.

النظام يرفع راية ولا يحكم. القرار للمالك: إما «العملية سليمة»
فتُقبل الإشارة وتُغلق، أو «مخالفة» فتُعكس قيودها بقيود مضادة.

العكس يمر عبر محرك القيود لا بتعديل مباشر — القيد الأصلي يبقى
مقرونًا بعكسه في السجل.
"""

from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import InvalidState
from apps.ledger.models import Transaction
from apps.ledger.services import AlreadyReversed, reverse_entry
from apps.pos.permissions import IsOwner, get_staff_user

from .models import FraudSignal


class FraudSignalSerializer(serializers.ModelSerializer):
    rule_label = serializers.SerializerMethodField()
    invoice_no = serializers.CharField(source="transaction.invoice_no", read_only=True)
    invoice_amount = serializers.DecimalField(
        source="transaction.invoice_amount", max_digits=12, decimal_places=2, read_only=True
    )
    customer_phone = serializers.CharField(source="transaction.customer.phone", read_only=True)
    staff_name = serializers.CharField(
        source="transaction.staff_user.user.full_name", read_only=True
    )
    branch_name = serializers.CharField(source="transaction.terminal.branch.name", read_only=True)

    class Meta:
        model = FraudSignal
        fields = (
            "id",
            "rule_code",
            "rule_label",
            "severity",
            "status",
            "details",
            "created_at",
            "reviewed_at",
            "invoice_no",
            "invoice_amount",
            "customer_phone",
            "staff_name",
            "branch_name",
        )
        read_only_fields = fields

    RULE_LABELS = {
        "same_customer_burst": "نفس العميل عدة مرات في دقائق",
        "cashier_burst": "كاشير يؤكّد عمليات كثيرة بسرعة",
        "round_amount": "مبلغ مستدير كبير",
        "staff_self_transaction": "الكاشير يمنح نقاطًا لرقمه",
        "outlier_amount": "فاتورة أكبر بكثير من متوسط الفرع",
    }

    def get_rule_label(self, signal) -> str:
        return self.RULE_LABELS.get(signal.rule_code, signal.rule_code)


class ResolveSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["accept", "reject"])
    note = serializers.CharField(max_length=200, required=False, allow_blank=True)


class FraudSignalListView(APIView):
    permission_classes = [IsOwner]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="status", type=str, description="open · accepted · rejected"),
            OpenApiParameter(name="severity", type=str, description="low · medium · high"),
        ],
        responses=FraudSignalSerializer(many=True),
        summary="إشارات تحتاج مراجعة",
    )
    def get(self, request):
        staff = get_staff_user(request)

        queryset = FraudSignal.objects.filter(
            transaction__terminal__branch__brand=staff.branch.brand
        ).select_related(
            "transaction__customer",
            "transaction__staff_user__user",
            "transaction__terminal__branch",
        )

        signal_status = request.query_params.get("status", FraudSignal.STATUS_OPEN)
        if signal_status != "all":
            queryset = queryset.filter(status=signal_status)

        severity = request.query_params.get("severity")
        if severity:
            queryset = queryset.filter(severity=severity)

        # الأخطر أولًا: المالك يراجع عددًا محدودًا قبل أن يملّ
        order = {"high": 0, "medium": 1, "low": 2}
        rows = sorted(
            queryset.order_by("-created_at")[:200],
            key=lambda s: (order.get(s.severity, 9), -s.created_at.timestamp()),
        )

        return Response(FraudSignalSerializer(rows, many=True).data)


class FraudSignalResolveView(APIView):
    permission_classes = [IsOwner]

    @extend_schema(
        request=ResolveSerializer,
        responses={200: None},
        summary="قبول الإشارة أو رفض العملية وعكس قيودها",
    )
    @transaction.atomic
    def post(self, request, pk):
        staff = get_staff_user(request)

        serializer = ResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data["action"]

        signal = FraudSignal.objects.select_for_update(of=("self",)).get(
            pk=pk, transaction__terminal__branch__brand=staff.branch.brand
        )

        if signal.status != FraudSignal.STATUS_OPEN:
            raise InvalidState("هذه الإشارة مراجَعة بالفعل.", code="already_reviewed")

        reversed_entries = []
        if action == "reject":
            reversed_entries = _reverse_transaction(signal.transaction, staff)

        signal.status = (
            FraudSignal.STATUS_ACCEPTED if action == "accept" else FraudSignal.STATUS_REJECTED
        )
        signal.reviewed_by = staff
        signal.reviewed_at = timezone.now()
        signal.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])

        return Response(
            {
                "id": str(signal.id),
                "status": signal.status,
                "reversed_entries": reversed_entries,
            },
            status=status.HTTP_200_OK,
        )


def _reverse_transaction(txn, staff) -> list[str]:
    """يعكس كل قيود العملية ويعلّمها معكوسة."""
    reversed_ids = []

    for entry in txn.entries.all():
        try:
            reversal = reverse_entry(entry, actor=staff)
        except AlreadyReversed:
            # قيد معكوس سابقًا لا يوقف عكس البقية
            continue
        reversed_ids.append(str(reversal.id))

    txn.status = Transaction.STATUS_REVERSED
    txn.save(update_fields=["status", "updated_at"])
    return reversed_ids
