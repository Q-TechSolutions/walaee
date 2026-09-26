"""
الدليل العام — الواجهة الوحيدة المفتوحة بلا مصادقة.

ما تُخرجه هذه الملفات يظهر لأي زائر على الإنترنت، فالقاعدة صارمة:
**لا بيانات عملاء ولا أرقام تشغيل**. لا عدد عمليات، ولا متوسط
فاتورة، ولا رصيد. علامة تجارية وفروعها وإحداثياتها معلومات معروضة
على الباب أصلًا؛ أما «كم عميلًا لدى هذا المتجر» فرقم تنافسي يخص
التاجر وحده.

العدّاد الوحيد الذي يخرج هو إجمالي المنصة مجمَّعًا — لا يكشف عن
متجر بعينه شيئًا.

التخزين المؤقت ليس تحسينًا هنا: هذا المسار هو أول ما يصيبه أي
ارتفاع في الزيارات، وصفحة هبوط تنهار تحت نجاحها التسويقي مفارقة
مكلفة. القيمة تُحسب مرة كل خمس دقائق وتُخدم من Redis.
"""

from __future__ import annotations

from django.core.cache import cache
from django.db.models import Count, Q
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import Customer
from apps.loyalty.models import Membership

from . import geo
from .models import Branch, Brand

CACHE_KEY = "public:network:v1"
CACHE_SECONDS = 300


class DirectoryThrottle(AnonRateThrottle):
    """
    حدّ خاص بالدليل، أوسع من حد المصادقة وأضيق من اللا نهاية.

    الصفحة العامة تطلبه مرة عند التحميل، فستّون طلبًا في الدقيقة من
    عنوان واحد ليست تصفّحًا — إما سكربت يكشط الدليل وإما خطأ في
    الواجهة يعيد الطلب في حلقة.
    """

    scope = "public_directory"
    rate = "60/min"


# ══════════════ المخطّطات ══════════════
# صريحة لا مولّدة من النموذج: النموذج يحمل حقولًا لا يجوز أن تخرج
# (مفاتيح داخلية، حالة الاشتراك)، والتوليد التلقائي يجعل إضافة
# حقل حسّاس للنموذج غدًا تسريبًا صامتًا اليوم.


class PublicBranchSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    city = serializers.CharField()
    governorate = serializers.CharField()
    governorate_name = serializers.CharField()
    address = serializers.CharField()
    lat = serializers.FloatField()
    lng = serializers.FloatField()
    brand_slug = serializers.CharField()
    brand_name = serializers.CharField()
    color = serializers.CharField()


class PublicBrandSerializer(serializers.Serializer):
    slug = serializers.CharField()
    name = serializers.CharField()
    category = serializers.CharField()
    tagline = serializers.CharField()
    color = serializers.CharField()
    logo = serializers.CharField(allow_null=True)
    branch_count = serializers.IntegerField()
    governorates = serializers.ListField(child=serializers.CharField())
    program_type = serializers.CharField(allow_null=True)
    joined_on = serializers.DateField(allow_null=True)


class GovernorateSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    region = serializers.CharField()
    lat = serializers.FloatField()
    lng = serializers.FloatField()
    branch_count = serializers.IntegerField()
    brand_count = serializers.IntegerField()


class StatsSerializer(serializers.Serializer):
    brands = serializers.IntegerField()
    branches = serializers.IntegerField()
    governorates = serializers.IntegerField()
    cities = serializers.IntegerField()
    members = serializers.IntegerField()
    categories = serializers.IntegerField()


class NetworkSerializer(serializers.Serializer):
    stats = StatsSerializer()
    brands = PublicBrandSerializer(many=True)
    branches = PublicBranchSerializer(many=True)
    governorates = GovernorateSerializer(many=True)
    categories = serializers.ListField(child=serializers.CharField())


# ══════════════ البناء ══════════════


def _rounded(value: int) -> int:
    """
    يُقرّب عدّاد الأعضاء إلى أقرب مئة للأسفل.

    الرقم الدقيق على صفحة عامة يتحوّل إلى قناة تسريب: زائر يراقب
    العدّاد يستطيع استنتاج متى ينضم عميل وأين. والتقريب لا يضيّع
    شيئًا — لا أحد يقرأ «١٢٬٤٣٧ عضوًا» بدقّة أكبر من «١٢٬٤٠٠».
    """
    if value < 100:
        return value
    return (value // 100) * 100


def build_network() -> dict:
    brands = (
        Brand.objects.filter(is_active=True, is_listed=True)
        .select_related("organization")
        .prefetch_related("programs")
        .annotate(
            live_branches=Count(
                "branches",
                filter=Q(branches__is_active=True, branches__lat__isnull=False),
                distinct=True,
            )
        )
        .order_by("name")
    )

    branch_rows = (
        Branch.objects.filter(
            is_active=True,
            lat__isnull=False,
            lng__isnull=False,
            brand__is_active=True,
            brand__is_listed=True,
        )
        .select_related("brand")
        .order_by("brand__name", "name")
    )

    branches: list[dict] = []
    by_governorate: dict[str, dict] = {}
    cities: set[str] = set()

    for branch in branch_rows:
        code = branch.governorate
        branches.append(
            {
                "id": str(branch.id),
                "name": branch.name,
                "city": branch.city,
                "governorate": code,
                "governorate_name": geo.name_of(code),
                "address": branch.address,
                "lat": float(branch.lat),
                "lng": float(branch.lng),
                "brand_slug": branch.brand.slug,
                "brand_name": branch.brand.name,
                "color": branch.brand.primary_color,
            }
        )
        if branch.city:
            cities.add(branch.city)

        if code:
            bucket = by_governorate.setdefault(code, {"branches": 0, "brands": set()})
            bucket["branches"] += 1
            bucket["brands"].add(branch.brand.slug)

    brand_rows: list[dict] = []
    categories: list[str] = []
    for brand in brands:
        if not brand.live_branches:
            # علامة تعاقدت ولم تفتح فرعًا بإحداثيات بعد: إدراجها
            # يجعل الخريطة تعد متجرًا لا يستطيع الزائر الذهاب إليه.
            continue

        codes = sorted(
            {
                b["governorate"]
                for b in branches
                if b["brand_slug"] == brand.slug and b["governorate"]
            }
        )
        program = next((p for p in brand.programs.all() if p.is_active), None)
        brand_rows.append(
            {
                "slug": brand.slug,
                "name": brand.name,
                "category": brand.category,
                "tagline": brand.tagline,
                "color": brand.primary_color,
                "logo": brand.logo.url if brand.logo else None,
                "branch_count": brand.live_branches,
                "governorates": codes,
                "program_type": program.type if program else None,
                "joined_on": brand.joined_on,
            }
        )
        if brand.category and brand.category not in categories:
            categories.append(brand.category)

    governorates = [
        {
            "code": g.code,
            "name": g.name,
            "region": g.region,
            "lat": g.anchor_lat,
            "lng": g.anchor_lng,
            "branch_count": by_governorate.get(g.code, {}).get("branches", 0),
            "brand_count": len(by_governorate.get(g.code, {}).get("brands", ())),
        }
        for g in geo.GOVERNORATES
    ]

    # العضويات لا العملاء: العميل الواحد قد يكون عضوًا في خمس
    # علامات، و«عدد المنضمّين» على صفحة عامة يعني أشخاصًا لا صفوفًا.
    members = (
        Membership.objects.filter(status=Membership.STATUS_ACTIVE)
        .values("customer_id")
        .distinct()
        .count()
    )
    if not members:
        members = Customer.objects.filter(deleted_at__isnull=True).count()

    return {
        "stats": {
            "brands": len(brand_rows),
            "branches": len(branches),
            "governorates": sum(1 for g in governorates if g["branch_count"]),
            "cities": len(cities),
            "members": _rounded(members),
            "categories": len(categories),
        },
        "brands": brand_rows,
        "branches": branches,
        "governorates": governorates,
        "categories": sorted(categories),
    }


class NetworkView(APIView):
    """شبكة المتاجر المتعاقدة — تغذّي الخريطة والصفحة العامة."""

    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [DirectoryThrottle]

    @extend_schema(
        responses=NetworkSerializer,
        summary="شبكة المتاجر المتعاقدة",
        description=(
            "بيانات عامة بلا مصادقة: العلامات وفروعها وإحداثياتها وتوزيعها "
            "على المحافظات. لا تحتوي أي بيانات عملاء."
        ),
        examples=[
            OpenApiExample(
                "نموذج",
                value={
                    "stats": {"brands": 15, "branches": 88, "governorates": 24},
                    "categories": ["مقاهٍ ومشروبات", "صيدليات"],
                },
                response_only=True,
            )
        ],
    )
    def get(self, request):
        payload = cache.get(CACHE_KEY)
        if payload is None:
            payload = build_network()
            cache.set(CACHE_KEY, payload, CACHE_SECONDS)

        response = Response(payload)
        # وسيط عام: الرد واحد لكل الزوّار ولا يحمل شيئًا خاصًّا بأحد،
        # فتخزينه على الحافة يقصّر أول رسم للصفحة إلى حد ملموس.
        response["Cache-Control"] = f"public, max-age={CACHE_SECONDS}"
        return response


def invalidate_network_cache() -> None:
    """يُستدعى بعد أي تغيير يمسّ الدليل — راجع `apps.tenancy.signals`."""
    cache.delete(CACHE_KEY)
