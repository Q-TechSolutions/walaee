"""
لوحة التاجر والتقارير.

كلها للقراءة عدا عكس القيد. الصلاحية تتبع الدور: الكاشير لا يرى
تقريرًا، والالتزام القائم للمالك وحده لأنه رقم مالي.

المرجع: docs/architecture/api-contract.md — القسم ٢
"""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing import services as billing
from apps.pos.permissions import IsCashier, IsManager, IsOwner, get_staff_user

from . import reports
from .models import LedgerEntry
from .services import reverse_entry

_DAYS = OpenApiParameter(name="days", type=int, description="طول الفترة بالأيام (افتراضيًا ٣٠)")


def _days(request, default: int = 30) -> int:
    """
    طول الفترة من الطلب.

    محدود بـ ٣٦٥: فترة غير محدودة تعني مسحًا كاملًا للجدول في كل
    فتح للوحة، وهو أول ما يبطئ النظام عند أول تاجر كبير.
    """
    try:
        value = int(request.query_params.get("days", default))
    except (TypeError, ValueError):
        return default
    return max(1, min(value, 365))


class MerchantDashboardView(APIView):
    permission_classes = [IsManager]

    @extend_schema(parameters=[_DAYS], responses={200: None}, summary="مؤشرات لوحة التاجر")
    def get(self, request):
        staff = get_staff_user(request)
        return Response(reports.dashboard(staff.branch.brand, days=_days(request)))


class MerchantSeriesView(APIView):
    permission_classes = [IsManager]

    @extend_schema(parameters=[_DAYS], responses={200: None}, summary="سلسلة يومية")
    def get(self, request):
        staff = get_staff_user(request)
        return Response({"series": reports.daily_series(staff.branch.brand, days=_days(request))})


class MerchantLiabilityView(APIView):
    # المالك وحده: رقم مالي يظهر في حسابات المتجر
    permission_classes = [IsOwner]

    @extend_schema(responses={200: None}, summary="الالتزام القائم")
    def get(self, request):
        staff = get_staff_user(request)
        return Response(reports.outstanding_liability(staff.branch.brand))


class MerchantSegmentsView(APIView):
    permission_classes = [IsManager]

    @extend_schema(responses={200: None}, summary="توزيع العملاء على الشرائح")
    def get(self, request):
        staff = get_staff_user(request)
        return Response(reports.customer_segments(staff.branch.brand))


class MerchantActivityView(APIView):
    """
    تدفّق ما يحدث عند الصندوق الآن.

    للمدير فما فوق: يعرض اسم العميل واسم الكاشير معًا، وهو ربط لا
    يخصّ كاشيرًا يرى زملاءه.
    """

    permission_classes = [IsManager]

    @extend_schema(responses={200: None}, summary="أحدث العمليات")
    def get(self, request):
        staff = get_staff_user(request)
        limit = min(int(request.query_params.get("limit", 12) or 12), 50)
        return Response({"activity": reports.recent_activity(staff.branch.brand, limit=limit)})


class CashierShiftView(APIView):
    """
    ملخّص وردية الكاشير الحالي.

    متاح للكاشير نفسه لا للمدير وحده: هو رقمه هو، ورؤيته لما أنجزه
    اليوم جزء من الشاشة التي يقف أمامها.
    """

    permission_classes = [IsCashier]

    @extend_schema(responses={200: None}, summary="مناوبة اليوم")
    def get(self, request):
        staff = get_staff_user(request)
        return Response(
            {
                **reports.cashier_shift(staff),
                "staff_name": staff.user.full_name,
                "role_label": staff.get_role_display(),
                "branch_name": staff.branch.name,
            }
        )


class MerchantReportView(APIView):
    permission_classes = [IsManager]

    KINDS = {
        "top-customers": lambda brand: {"rows": reports.top_customers(brand)},
        "branches": lambda brand: {"rows": reports.branch_performance(brand)},
        "programs": lambda brand: {"rows": reports.program_performance(brand)},
    }

    @extend_schema(responses={200: None}, summary="تقرير قابل للتصدير")
    def get(self, request, kind):
        staff = get_staff_user(request)
        builder = self.KINDS.get(kind)

        if builder is None:
            return Response(
                {
                    "error": {
                        "code": "unknown_report",
                        "message": "تقرير غير معروف.",
                        "details": {"available": sorted(self.KINDS)},
                    }
                },
                status=404,
            )

        # التصدير ميزة مدفوعة — القراءة على الشاشة ليست كذلك
        if request.query_params.get("export") == "1":
            billing.require_feature(staff.branch.brand.organization, "reports_export")

        return Response({"kind": kind, **builder(staff.branch.brand)})


class ReverseEntryView(APIView):
    # عكس قيد يغيّر رصيد عميل — المالك وحده
    permission_classes = [IsOwner]

    @extend_schema(request=None, responses={200: None}, summary="عكس قيد بقيد مضاد")
    def post(self, request, pk):
        staff = get_staff_user(request)

        entry = LedgerEntry.objects.select_related("membership").get(
            pk=pk, membership__brand=staff.branch.brand
        )
        reversal = reverse_entry(entry, actor=staff)

        return Response(
            {
                "reversed_entry": str(entry.id),
                "reversal_entry": str(reversal.id),
                "delta": str(reversal.delta),
                "balance_after": str(reversal.balance_after),
            }
        )
