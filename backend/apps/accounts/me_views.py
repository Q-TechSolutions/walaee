"""
نقاط حساب العميل: المحفظة والنشاط والخصوصية.

الخصوصية ليست ميزة إضافية هنا: `GET /me/export` و `DELETE /me`
شرطان للامتثال، وبناؤهما بعد الإطلاق يعني تعديل كل مسار يمسّ بيانات
العميل. المرجع: docs/architecture/security.md
"""

from django.db import transaction
from django.db.models import Max, Sum
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import DomainError
from apps.common.pagination import DefaultPagination
from apps.ledger.models import LedgerEntry, Redemption, Transaction
from apps.loyalty.models import Balance, Membership
from apps.pos.permissions import IsCustomer

from . import services
from .models import Customer, OtpCode
from .serializers import CustomerSerializer


class CardSerializer(serializers.Serializer):
    """بطاقة علامة واحدة في محفظة العميل."""

    brand_id = serializers.UUIDField()
    brand_name = serializers.CharField()
    primary_color = serializers.CharField()
    category = serializers.CharField()
    joined_at = serializers.DateTimeField()
    tier = serializers.CharField()
    last_activity = serializers.DateTimeField(allow_null=True)
    balances = serializers.ListField()


def _card(membership) -> dict:
    return {
        "membership_id": str(membership.id),
        "brand_id": str(membership.brand_id),
        "brand_name": membership.brand.name,
        "primary_color": membership.brand.primary_color,
        "category": membership.brand.category,
        "joined_at": membership.joined_at,
        "tier": membership.tier,
        "last_activity": getattr(membership, "last_activity", None),
        "balances": [
            {
                "program_id": str(balance.program_id),
                "program_name": balance.program.name,
                "program_type": balance.program.type,
                "unit_label": balance.program.unit_label,
                "amount": str(balance.amount),
                "expires_at": balance.expires_at,
            }
            for balance in membership.balances.all()
        ],
    }


class MeView(APIView):
    permission_classes = [IsCustomer]

    @extend_schema(responses=CustomerSerializer, summary="الملف الشخصي")
    def get(self, request):
        return Response(CustomerSerializer(request.user).data)

    @extend_schema(
        request=CustomerSerializer,
        responses=CustomerSerializer,
        summary="تعديل الاسم وتاريخ الميلاد",
    )
    def patch(self, request):
        serializer = CustomerSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class MyCardsView(APIView):
    permission_classes = [IsCustomer]

    @extend_schema(responses=CardSerializer(many=True), summary="محفظة البطاقات")
    def get(self, request):
        memberships = (
            Membership.objects.filter(customer=request.user)
            .select_related("brand")
            .prefetch_related("balances__program")
            .annotate(last_activity=Max("entries__created_at"))
            # الأحدث نشاطًا أولًا: العميل يفتح التطبيق ليستخدم
            # البطاقة التي يتعامل معها الآن لا التي سجّل بها أولًا
            .order_by("-last_activity", "-joined_at")
        )
        return Response([_card(m) for m in memberships])


class CardDetailView(APIView):
    permission_classes = [IsCustomer]

    @extend_schema(responses=CardSerializer, summary="تفاصيل بطاقة")
    def get(self, request, brand_id):
        membership = (
            Membership.objects.filter(customer=request.user, brand_id=brand_id)
            .select_related("brand")
            .prefetch_related("balances__program")
            .annotate(last_activity=Max("entries__created_at"))
            .first()
        )

        if membership is None:
            return Response(
                {
                    "error": {
                        "code": "not_a_member",
                        "message": "لست عضوًا في هذه العلامة بعد.",
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        rewards = [
            {
                "id": str(reward.id),
                "title": reward.title,
                "description": reward.description,
                "cost_amount": str(reward.cost_amount),
                "unit_label": reward.program.unit_label,
                "program_id": str(reward.program_id),
                "in_stock": reward.in_stock,
            }
            for reward in _brand_rewards(membership.brand)
        ]

        entries = (
            LedgerEntry.objects.filter(membership=membership)
            .select_related("program")
            .order_by("-created_at")[:20]
        )

        return Response(
            {
                **_card(membership),
                "rewards": rewards,
                "activity": [_entry(entry) for entry in entries],
                "total_spend": str(
                    Transaction.objects.filter(
                        customer=request.user,
                        terminal__branch__brand=membership.brand,
                        status=Transaction.STATUS_CONFIRMED,
                    ).aggregate(total=Sum("invoice_amount"))["total"]
                    or 0
                ),
            }
        )


def _brand_rewards(brand):
    from apps.loyalty.models import Reward

    return (
        Reward.objects.filter(program__brand=brand, is_active=True)
        .select_related("program")
        .order_by("cost_amount")
    )


def _entry(entry) -> dict:
    return {
        "id": str(entry.id),
        "delta": str(entry.delta),
        "reason": entry.reason,
        "reason_label": entry.get_reason_display(),
        "program": entry.program.name,
        "unit_label": entry.program.unit_label,
        "balance_after": str(entry.balance_after),
        "created_at": entry.created_at.isoformat(),
    }


class MyActivityView(APIView):
    permission_classes = [IsCustomer]

    @extend_schema(responses={200: None}, summary="سجل النشاط مع ترقيم")
    def get(self, request):
        queryset = (
            LedgerEntry.objects.filter(membership__customer=request.user)
            .select_related("program", "membership__brand")
            .order_by("-created_at")
        )

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)

        return paginator.get_paginated_response(
            [{**_entry(entry), "brand_name": entry.membership.brand.name} for entry in (page or [])]
        )


class MyRedemptionsView(APIView):
    permission_classes = [IsCustomer]

    @extend_schema(responses={200: None}, summary="أكواد الاستبدال")
    def get(self, request):
        redemptions = (
            Redemption.objects.filter(membership__customer=request.user)
            .select_related("reward", "membership__brand")
            .order_by("-created_at")[:30]
        )

        return Response(
            [
                {
                    "id": str(item.id),
                    "code": item.code,
                    "status": item.status,
                    "reward_title": item.reward.title,
                    "brand_name": item.membership.brand.name,
                    "expires_at": item.expires_at,
                    "used_at": item.used_at,
                }
                for item in redemptions
            ]
        )


class PushSubscriptionView(APIView):
    permission_classes = [IsCustomer]

    @extend_schema(request=None, responses={200: None}, summary="تسجيل اشتراك Web Push")
    def post(self, request):
        subscription = request.data.get("subscription")

        if not isinstance(subscription, dict) or "endpoint" not in subscription:
            raise DomainError("اشتراك غير صالح.", code="invalid_subscription")

        customer = request.user
        customer.push_subscription = subscription
        customer.save(update_fields=["push_subscription", "updated_at"])

        # الإشعار المجاني يقلّل تكلفة الحملات على التاجر بأضعاف،
        # فتسجيله نجاح تشغيلي يستحق التأكيد للواجهة
        return Response({"enabled": True})

    @extend_schema(responses={200: None}, summary="إلغاء الإشعارات")
    def delete(self, request):
        customer = request.user
        customer.push_subscription = None
        customer.save(update_fields=["push_subscription", "updated_at"])
        return Response({"enabled": False})


class ExportMyDataView(APIView):
    permission_classes = [IsCustomer]

    @extend_schema(responses={200: None}, summary="تحميل نسخة من بياناتي")
    def get(self, request):
        """
        كل ما تحتفظ به المنصة عن هذا العميل.

        يُبنى من الجداول مباشرة لا من كاش: نسخة ناقصة أسوأ من عدمها
        لأنها تعطي انطباعًا زائفًا بالشفافية.
        """
        customer = request.user

        memberships = (
            Membership.objects.filter(customer=customer)
            .select_related("brand")
            .prefetch_related("balances__program")
        )
        entries = LedgerEntry.objects.filter(membership__customer=customer).select_related(
            "program", "membership__brand"
        )
        transactions = Transaction.objects.filter(customer=customer).select_related(
            "terminal__branch__brand"
        )

        return Response(
            {
                "generated_at": timezone.now().isoformat(),
                "profile": {
                    "id": str(customer.id),
                    "phone": customer.phone,
                    "full_name": customer.full_name,
                    "birth_date": customer.birth_date,
                    "consent_at": customer.consent_at,
                    "consent_version": customer.consent_version,
                    "created_at": customer.created_at,
                },
                "memberships": [
                    {
                        "brand": m.brand.name,
                        "joined_at": m.joined_at,
                        "tier": m.tier,
                        "balances": [
                            {
                                "program": b.program.name,
                                "amount": str(b.amount),
                                "expires_at": b.expires_at,
                            }
                            for b in m.balances.all()
                        ],
                    }
                    for m in memberships
                ],
                "ledger": [
                    {
                        "brand": e.membership.brand.name,
                        "program": e.program.name,
                        "delta": str(e.delta),
                        "reason": e.reason,
                        "balance_after": str(e.balance_after),
                        "created_at": e.created_at,
                    }
                    for e in entries
                ],
                "transactions": [
                    {
                        "brand": t.terminal.branch.brand.name,
                        "branch": t.terminal.branch.name,
                        "invoice_no": t.invoice_no,
                        "invoice_amount": str(t.invoice_amount),
                        "status": t.status,
                        "created_at": t.created_at,
                    }
                    for t in transactions
                ],
            }
        )


class DeleteAccountView(APIView):
    permission_classes = [IsCustomer]

    @extend_schema(request=None, responses={200: None}, summary="طلب كود حذف الحساب")
    def post(self, request):
        """
        حذف الحساب يتطلب كودًا جديدًا حتى لو كانت الجلسة مفتوحة.

        هاتف مفتوح في يد شخص آخر لا يجب أن يمحو حساب صاحبه بضغطتين.
        """
        services.request_otp(phone=request.user.phone, purpose=OtpCode.PURPOSE_DELETE)
        return Response({"sent": True})

    @extend_schema(request=None, responses={200: None}, summary="تأكيد حذف الحساب")
    @transaction.atomic
    def delete(self, request):
        code = request.data.get("code") or request.query_params.get("code", "")

        services.verify_otp(
            phone=request.user.phone,
            code=str(code),
            purpose=OtpCode.PURPOSE_DELETE,
        )

        customer: Customer = request.user
        customer.anonymize()

        # القيود تبقى بمعرّف مجهول: حق العميل محترم ورصيد التاجر
        # متوازن — التعارض المحلول في docs/architecture/security.md
        return Response(
            {
                "deleted": True,
                "message": (
                    "حُذفت بياناتك الشخصية. سجلات المعاملات تبقى بمعرّف "
                    "مجهول لأن أرصدة المتاجر محسوبة عليها."
                ),
            }
        )


class NearbyStoresView(APIView):
    permission_classes = [IsCustomer]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="lat", type=float, required=True),
            OpenApiParameter(name="lng", type=float, required=True),
            OpenApiParameter(name="radius_km", type=float),
        ],
        responses={200: None},
        summary="متاجر قريبة منك",
    )
    def get(self, request):
        """
        بحث جغرافي بصندوق إحداثيات.

        صندوق لا دائرة، وبلا PostGIS: الفرق في الدقة على مسافات
        المدينة لا يُلاحظ، والمقابل امتداد قاعدة بيانات إضافي
        وتعقيد نشر لا يبرّرهما نطاق المرحلة الحالية.
        """
        from apps.tenancy.models import Branch

        try:
            lat = float(request.query_params.get("lat", ""))
            lng = float(request.query_params.get("lng", ""))
        except ValueError:
            raise DomainError("الإحداثيات مطلوبة.", code="missing_coordinates") from None

        try:
            radius = min(float(request.query_params.get("radius_km", 10)), 50)
        except ValueError:
            radius = 10.0

        # درجة عرض ≈ ١١١ كم. درجة الطول تضيق مع الاقتراب من القطبين،
        # لكن التصحيح غير مهم على نطاق مدينة.
        delta = radius / 111.0

        branches = (
            Branch.objects.filter(
                is_active=True,
                brand__is_active=True,
                lat__gte=lat - delta,
                lat__lte=lat + delta,
                lng__gte=lng - delta,
                lng__lte=lng + delta,
            )
            .select_related("brand")
            .order_by("brand__name")[:50]
        )

        joined = set(
            Membership.objects.filter(customer=request.user).values_list("brand_id", flat=True)
        )

        rows = []
        for branch in branches:
            distance = _distance_km(lat, lng, branch.lat, branch.lng)
            if distance is None or distance > radius:
                continue
            rows.append(
                {
                    "branch_id": str(branch.id),
                    "branch_name": branch.name,
                    "address": branch.address,
                    "brand_id": str(branch.brand_id),
                    "brand_name": branch.brand.name,
                    "primary_color": branch.brand.primary_color,
                    "category": branch.brand.category,
                    "is_member": branch.brand_id in joined,
                    "distance_km": round(distance, 2),
                }
            )

        rows.sort(key=lambda row: row["distance_km"])
        return Response(rows)


def _distance_km(lat1, lng1, lat2, lng2) -> float | None:
    """مسافة هافرساين. None حين لا إحداثيات للفرع."""
    if lat2 is None or lng2 is None:
        return None

    from math import asin, cos, radians, sin, sqrt

    lat2, lng2 = float(lat2), float(lng2)
    d_lat = radians(lat2 - lat1)
    d_lng = radians(lng2 - lng1)

    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lng / 2) ** 2
    return 2 * 6371 * asin(sqrt(a))


class MyBalancesSummaryView(APIView):
    permission_classes = [IsCustomer]

    @extend_schema(responses={200: None}, summary="ملخّص المحفظة")
    def get(self, request):
        """رقم واحد يراه العميل أول ما يفتح التطبيق."""
        totals = (
            Balance.objects.filter(membership__customer=request.user)
            .values("program__type")
            .annotate(total=Sum("amount"))
        )

        return Response(
            {
                "cards": Membership.objects.filter(customer=request.user).count(),
                "by_type": {row["program__type"]: str(row["total"] or 0) for row in totals},
                "pending_redemptions": Redemption.objects.filter(
                    membership__customer=request.user,
                    status=Redemption.STATUS_PENDING,
                    expires_at__gt=timezone.now(),
                ).count(),
            }
        )
