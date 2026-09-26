"""
نقاط نقطة البيع وتطبيق العميل.

المرجع: docs/architecture/api-contract.md
"""

from decimal import Decimal

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Customer
from apps.ledger.models import Transaction
from apps.ledger.services import redeem_reward, use_redemption
from apps.loyalty.models import Membership, Reward

from . import codes, services
from .permissions import IsCashier, IsCustomer, get_staff_user
from .serializers import (
    MyRewardSerializer,
    RedeemRequestSerializer,
    RedemptionSerializer,
    ResolveCodeSerializer,
    TerminalCodeSerializer,
    TransactionCreateSerializer,
    TransactionSerializer,
)


def _current_customer(request) -> Customer:
    """
    العميل صاحب التوكن.

    المصادقة حلّته بالفعل وتحققت من أنه غير محذوف — راجع
    apps.accounts.authentication.WalaeeJWTAuthentication
    """
    return request.user


# ═══════════════════════ شاشة الكاشير ═══════════════════════


class TerminalCodeView(APIView):
    permission_classes = [IsCashier]

    @extend_schema(responses=TerminalCodeSerializer, summary="الرمز الفعّال للطرفية")
    def get(self, request):
        staff = get_staff_user(request)
        terminal = staff.branch.terminals.filter(is_active=True).first()
        if terminal is None:
            return Response(
                {"error": {"code": "no_terminal", "message": "لا توجد نقطة بيع نشطة."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        code = codes.current_code(terminal.id) or codes.issue_code(terminal.id)
        return Response(
            TerminalCodeSerializer(
                {"terminal_id": terminal.id, "label": terminal.label, "code": code}
            ).data
        )

    @extend_schema(request=None, responses=TerminalCodeSerializer, summary="تجديد فوري للرمز")
    def post(self, request):
        staff = get_staff_user(request)
        terminal = staff.branch.terminals.filter(is_active=True).first()
        if terminal is None:
            return Response(
                {"error": {"code": "no_terminal", "message": "لا توجد نقطة بيع نشطة."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        code = codes.issue_code(terminal.id)
        return Response(
            TerminalCodeSerializer(
                {"terminal_id": terminal.id, "label": terminal.label, "code": code}
            ).data
        )


class PendingTransactionsView(APIView):
    permission_classes = [IsCashier]

    @extend_schema(responses=TransactionSerializer(many=True), summary="العمليات المعلّقة")
    def get(self, request):
        staff = get_staff_user(request)
        queryset = (
            Transaction.objects.filter(
                terminal__branch=staff.branch, status=Transaction.STATUS_PENDING
            )
            .select_related("customer", "terminal")
            .order_by("created_at")[:50]
        )
        return Response(TransactionSerializer(queryset, many=True).data)


class ConfirmTransactionView(APIView):
    permission_classes = [IsCashier]

    @extend_schema(
        request=None,
        responses=TransactionSerializer,
        summary="تأكيد العملية ومنح النقاط",
    )
    def post(self, request, pk):
        staff = get_staff_user(request)
        services.confirm_transaction(pk, staff_user=staff)

        txn = Transaction.objects.select_related("customer", "terminal").get(pk=pk)
        return Response(TransactionSerializer(txn).data)


class ManualTransactionView(APIView):
    permission_classes = [IsCashier]

    @extend_schema(
        request=TransactionCreateSerializer,
        responses=TransactionSerializer,
        summary="المسار اليدوي: هاتف + فاتورة",
    )
    def post(self, request):
        serializer = TransactionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        staff = get_staff_user(request)
        txn = services.create_manual_transaction(
            staff_user=staff,
            phone=data["phone"],
            invoice_amount=data["invoice_amount"],
            invoice_no=data["invoice_no"],
        )
        services.confirm_transaction(txn.id, staff_user=staff)

        txn.refresh_from_db()
        return Response(TransactionSerializer(txn).data, status=status.HTTP_201_CREATED)


class UseRedemptionView(APIView):
    permission_classes = [IsCashier]

    @extend_schema(request=None, responses=RedemptionSerializer, summary="صرف كود استبدال")
    def post(self, request, code):
        staff = get_staff_user(request)
        redemption = use_redemption(code=code, staff_user=staff)
        return Response(RedemptionSerializer(redemption).data)


# ═══════════════════════ تطبيق العميل ═══════════════════════


class ResolveCodeView(APIView):
    permission_classes = [IsCustomer]

    @extend_schema(
        request=ResolveCodeSerializer,
        responses={200: None},
        summary="ترجمة رمز QR إلى نقطة بيع",
    )
    def post(self, request):
        serializer = ResolveCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        terminal = services.resolve_terminal(serializer.validated_data["code"])
        brand = terminal.branch.brand
        customer = _current_customer(request)

        membership = Membership.objects.filter(customer=customer, brand=brand).first()
        balances = (
            [
                {
                    "program": str(b.program_id),
                    "program_name": b.program.name,
                    "amount": str(b.amount),
                    "unit": b.program.unit_label,
                }
                for b in membership.balances.select_related("program")
            ]
            if membership
            else []
        )

        return Response(
            {
                "terminal": {"id": str(terminal.id), "label": terminal.label},
                "branch": {"id": str(terminal.branch_id), "name": terminal.branch.name},
                "brand": {
                    "id": str(brand.id),
                    "name": brand.name,
                    "primary_color": brand.primary_color,
                },
                "is_member": membership is not None,
                "balances": balances,
            }
        )


class CreateTransactionView(APIView):
    permission_classes = [IsCustomer]

    @extend_schema(
        request=TransactionCreateSerializer,
        responses=TransactionSerializer,
        summary="إنشاء عملية معلّقة — لا تُمنح نقاط هنا",
    )
    def post(self, request):
        serializer = TransactionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        txn = services.create_transaction(
            code=data["code"],
            customer=_current_customer(request),
            invoice_amount=data["invoice_amount"],
            invoice_no=data["invoice_no"],
        )
        return Response(TransactionSerializer(txn).data, status=status.HTTP_201_CREATED)


class MyRewardsView(APIView):
    """
    المكافآت المتاحة للعميل — ومعها وقفته من كل واحدة.

    الرصيد جزء من الرد لا نداء ثانٍ: الشاشة تفصل «جاهزة للاستبدال»
    عن «قريبة منك»، وبلا الرصيد لا تستطيع التفرقة فتعرض الكل صفًا
    واحدًا بلا زر استبدال — وهو ما كان يحدث. العميل الواقف عند
    الكاشير لا يريد قائمة، يريد أن يعرف ماذا يصرف الآن.
    """

    permission_classes = [IsCustomer]

    @extend_schema(responses=MyRewardSerializer(many=True), summary="المكافآت المتاحة")
    def get(self, request):
        customer = _current_customer(request)
        memberships = list(
            Membership.objects.filter(customer=customer)
            .select_related("brand")
            .prefetch_related("balances")
        )

        # الرصيد لكل برنامج مرة واحدة، لا استعلام داخل الحلقة
        standing = {
            str(balance.program_id): balance.amount
            for membership in memberships
            for balance in membership.balances.all()
        }
        brands = {membership.brand_id: membership.brand for membership in memberships}

        rewards = (
            Reward.objects.filter(program__brand_id__in=list(brands), is_active=True)
            .select_related("program__brand")
            .order_by("cost_amount")
        )

        rows = []
        for reward in rewards:
            balance = standing.get(str(reward.program_id), Decimal("0"))
            cost = reward.cost_amount
            remaining = max(cost - balance, Decimal("0"))
            brand = reward.program.brand
            rows.append(
                {
                    "id": str(reward.id),
                    "title": reward.title,
                    "description": reward.description,
                    "cost_amount": _money(cost),
                    "cost_unit": reward.cost_unit,
                    "unit_label": reward.program.unit_label,
                    "stock": reward.stock,
                    "in_stock": reward.in_stock,
                    "brand_id": str(brand.id),
                    "brand_name": brand.name,
                    "primary_color": brand.primary_color,
                    "program_id": str(reward.program_id),
                    "program_name": reward.program.name,
                    "balance": _money(balance),
                    "remaining": _money(remaining),
                    # «جاهزة» تعني قابلة للصرف الآن: الرصيد كافٍ
                    # والمخزون غير منتهٍ. أحدهما وحده يعد بما لا يُصرف
                    "ready": remaining <= 0 and reward.in_stock,
                    "progress": _reward_progress(balance, cost),
                }
            )

        # الجاهز أولًا، ثم الأقرب اكتمالًا: ترتيب الشاشة هو ترتيب
        # ما يفعله العميل، لا ترتيب التكلفة
        rows.sort(key=lambda row: (not row["ready"], -row["progress"]))
        return Response(rows)


def _money(value: Decimal) -> str:
    """
    مبلغ بمنزلتين عشريتين دائمًا.

    `str(Decimal('0'))` يعطي «0» بينما رصيد محفوظ في القاعدة
    يعطي «0.00». رد يحمل الشكلين لنفس الحقل يكسر أي قارئ يقارن
    النصوص، ويظهر في الواجهة رصيدًا بلا كسور بجوار آخر بكسور.
    """
    return str(value.quantize(Decimal("0.01")))


def _reward_progress(balance: Decimal, cost: Decimal) -> float:
    """نسبة الاقتراب من المكافأة، محصورة بين صفر وواحد."""
    if cost <= 0:
        return 1.0
    return min(float(balance / cost), 1.0)


class RedeemView(APIView):
    permission_classes = [IsCustomer]

    @extend_schema(
        request=RedeemRequestSerializer,
        responses=RedemptionSerializer,
        summary="استبدال مكافأة",
    )
    def post(self, request):
        serializer = RedeemRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reward = get_object_or_404(
            Reward.objects.select_related("program"),
            pk=serializer.validated_data["reward_id"],
            is_active=True,
        )

        customer = _current_customer(request)
        membership = get_object_or_404(
            Membership, customer=customer, brand_id=reward.program.brand_id
        )

        redemption = redeem_reward(membership=membership, reward=reward, actor=customer)
        return Response(RedemptionSerializer(redemption).data, status=status.HTTP_201_CREATED)
