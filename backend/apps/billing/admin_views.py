"""
لوحة إدارة المنصة.

تعرض صحة الأعمال لا بيانات العملاء: `platform_admin` يرى المتاجر
والاشتراكات والإيراد، ولا يرى ماذا اشترى فرد بعينه. الفصل ليس
تهذيبًا — بيانات شراء الأفراد ملك التاجر وعميله، والمنصة وسيط.

المرجع: docs/architecture/security.md — مصفوفة الأدوار
"""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Customer
from apps.ledger.models import LedgerEntry, Transaction
from apps.loyalty.models import Membership
from apps.tenancy.models import Branch, Brand, Organization

from .models import Invoice, Plan, Subscription
from .services import mark_invoice_paid


class IsPlatformAdmin(BasePermission):
    message = "هذه اللوحة لفريق المنصة فقط."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return False
        # العميل ليس مستخدمًا ولا يملك هذه السمات أصلًا
        return bool(
            getattr(user, "is_platform_admin", False) or getattr(user, "is_superuser", False)
        )


class PlatformOverviewView(APIView):
    permission_classes = [IsPlatformAdmin]

    @extend_schema(responses={200: None}, summary="صحة المنصة")
    def get(self, request):
        now = timezone.now()
        month_ago = now - timedelta(days=30)

        subscriptions = Subscription.objects.exclude(status=Subscription.STATUS_CANCELLED)
        paying = subscriptions.exclude(plan=Plan.FREE)

        confirmed_month = Transaction.objects.filter(
            status=Transaction.STATUS_CONFIRMED, created_at__gte=month_ago
        )

        return Response(
            {
                "mrr": str(paying.aggregate(total=Sum("mrr"))["total"] or Decimal("0")),
                "organizations": {
                    "total": Organization.objects.count(),
                    "paying": paying.count(),
                    "free": subscriptions.filter(plan=Plan.FREE).count(),
                    "past_due": subscriptions.filter(status=Subscription.STATUS_PAST_DUE).count(),
                },
                "brands": Brand.objects.count(),
                "branches": Branch.objects.count(),
                "customers": {
                    "total": Customer.objects.filter(deleted_at__isnull=True).count(),
                    "new_30d": Customer.objects.filter(
                        created_at__gte=month_ago, deleted_at__isnull=True
                    ).count(),
                },
                "memberships": Membership.objects.count(),
                "transactions_30d": confirmed_month.count(),
                "gmv_30d": str(
                    confirmed_month.aggregate(total=Sum("invoice_amount"))["total"] or Decimal("0")
                ),
                "entries_30d": LedgerEntry.objects.filter(created_at__gte=month_ago).count(),
                "unpaid_invoices": Invoice.objects.filter(status=Invoice.STATUS_ISSUED).count(),
                "by_plan": {
                    row["plan"]: row["count"]
                    for row in subscriptions.values("plan").annotate(count=Count("id"))
                },
            }
        )


class PlatformMerchantsView(APIView):
    permission_classes = [IsPlatformAdmin]

    @extend_schema(responses={200: None}, summary="المتاجر واشتراكاتها")
    def get(self, request):
        """
        قائمة المؤسسات بمؤشرات نشاطها.

        «آخر نشاط» أهم عمود هنا: مؤسسة بلا عملية منذ أسبوعين هي
        مؤسسة على وشك الإلغاء، والتدخل قبل ذلك أرخص من استعادتها.
        """
        month_ago = timezone.now() - timedelta(days=30)

        organizations = (
            Organization.objects.select_related("subscription")
            .prefetch_related("brands")
            .annotate(
                brand_count=Count("brands", distinct=True),
                txn_count=Count(
                    "brands__branches__terminals__transactions",
                    filter=Q(
                        brands__branches__terminals__transactions__status=(
                            Transaction.STATUS_CONFIRMED
                        ),
                        brands__branches__terminals__transactions__created_at__gte=(month_ago),
                    ),
                    distinct=True,
                ),
            )
            .order_by("name")
        )

        rows = []
        for org in organizations:
            subscription = getattr(org, "subscription", None)
            last = (
                Transaction.objects.filter(
                    terminal__branch__brand__organization=org,
                    status=Transaction.STATUS_CONFIRMED,
                )
                .order_by("-created_at")
                .values_list("created_at", flat=True)
                .first()
            )

            rows.append(
                {
                    "id": str(org.id),
                    "name": org.name,
                    "status": org.status,
                    "brands": org.brand_count,
                    "brand_names": [brand.name for brand in org.brands.all()[:3]],
                    "plan": subscription.plan if subscription else "free",
                    "plan_label": (subscription.get_plan_display() if subscription else "مجانية"),
                    "subscription_status": (subscription.status if subscription else "trial"),
                    "mrr": str(subscription.mrr if subscription else Decimal("0")),
                    "transactions_30d": org.txn_count,
                    "last_activity": last.isoformat() if last else None,
                }
            )

        return Response(rows)


class PlatformInvoicesView(APIView):
    permission_classes = [IsPlatformAdmin]

    @extend_schema(responses={200: None}, summary="الفواتير غير المسدّدة")
    def get(self, request):
        invoices = (
            Invoice.objects.select_related("subscription__organization")
            .exclude(status=Invoice.STATUS_PAID)
            .order_by("issued_at")[:100]
        )

        return Response(
            [
                {
                    "id": str(invoice.id),
                    "number": invoice.number,
                    "organization": invoice.subscription.organization.name,
                    "amount": str(invoice.total),
                    "status": invoice.status,
                    "issued_at": invoice.issued_at,
                    "period_end": invoice.period_end,
                }
                for invoice in invoices
            ]
        )


class PlatformMarkPaidView(APIView):
    permission_classes = [IsPlatformAdmin]

    @extend_schema(request=None, responses={200: None}, summary="تعليم فاتورة كمسدّدة")
    def post(self, request, pk):
        """
        السداد يُعلَّم يدويًا في التحويل البنكي.

        ليس حلًّا مؤقتًا: أول عملاء المنصة يسدّدون بالتحويل فعلًا،
        والمطابقة مع كشف الحساب فعل بشري بطبيعته.
        """
        invoice = Invoice.objects.select_related("subscription").get(pk=pk)
        reference = str(request.data.get("reference", ""))[:120]

        mark_invoice_paid(invoice, reference=reference)

        return Response(
            {
                "id": str(invoice.id),
                "number": invoice.number,
                "status": invoice.status,
                "paid_at": invoice.paid_at,
            }
        )
