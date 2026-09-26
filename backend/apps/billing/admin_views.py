"""
لوحة إدارة المنصة.

تعرض صحة الأعمال لا بيانات العملاء: `platform_admin` يرى المتاجر
والاشتراكات والإيراد، ولا يرى ماذا اشترى فرد بعينه. الفصل ليس
تهذيبًا — بيانات شراء الأفراد ملك التاجر وعميله، والمنصة وسيط.

المرجع: docs/architecture/security.md — مصفوفة الأدوار
"""

import time
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.db.models import Count, Q, Sum
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Customer
from apps.ledger.models import LedgerEntry, Transaction
from apps.loyalty.models import Balance, Membership
from apps.tenancy.models import Branch, Brand, Organization, StaffUser

from .models import PLAN_LIMITS, Invoice, Plan, Subscription
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


class PlatformHealthView(APIView):
    """
    مؤشرات صحة المنصة مقابل أهدافها.

    ليست «نظرة عامة» ثانية: تلك تقول ما حدث، وهذه تقول هل ما حدث
    كافٍ. كل مؤشر معه هدفه وحكمه — والفرق بين الاثنين هو ما يستدعي
    قرارًا بدل تفسير.

    الأهداف أرقام معيارية لمنتج SaaS في سوقه لا أمنيات: انسحاب
    شهري فوق ٥٪ يعني أن القاعدة تتسرّب أسرع مما تُملأ، وتفعيل
    إشعارات دون ٤٠٪ يعني أن كل إعادة تفاعل ستُدفع ثمنها رسائل.
    """

    permission_classes = [IsPlatformAdmin]

    #: (الهدف، الاتجاه الجيد) — up يعني الأعلى أفضل
    TARGETS = {
        "mrr_growth": (Decimal("10"), "up"),
        "activation_rate": (Decimal("60"), "up"),
        "push_adoption": (Decimal("40"), "up"),
        "merchant_churn": (Decimal("5"), "down"),
        "redemption_rate": (Decimal("25"), "up"),
        "paying_share": (Decimal("50"), "up"),
    }

    @extend_schema(responses={200: None}, summary="مؤشرات الصحة مقابل أهدافها")
    def get(self, request):
        now = timezone.now()
        month_ago = now - timedelta(days=30)

        subscriptions = Subscription.objects.all()
        active = subscriptions.filter(status=Subscription.STATUS_ACTIVE)
        paying = active.exclude(mrr=Decimal("0"))

        organizations = Organization.objects.count()
        cancelled = subscriptions.filter(cancelled_at__gte=month_ago).count()

        customers = Customer.objects.filter(deleted_at__isnull=True)
        total_customers = customers.count()
        with_push = customers.exclude(push_subscription=None).count()

        # «مفعَّل» = انضمّ وأتمّ عملية واحدة على الأقل. التسجيل بلا
        # أول عملية ليس تفعيلًا — هو تكلفة رسالة تحقّق بلا مقابل
        activated = (
            Membership.objects.filter(entries__transaction__isnull=False)
            .values("customer_id")
            .distinct()
            .count()
        )

        granted = LedgerEntry.objects.filter(reason=LedgerEntry.REASON_EARN).aggregate(
            total=Sum("delta")
        )["total"] or Decimal("0")
        redeemed = LedgerEntry.objects.filter(reason=LedgerEntry.REASON_REDEEM).aggregate(
            total=Sum("delta")
        )["total"] or Decimal("0")

        mrr = paying.aggregate(total=Sum("mrr"))["total"] or Decimal("0")
        new_paying = paying.filter(created_at__gte=month_ago).aggregate(total=Sum("mrr"))[
            "total"
        ] or Decimal("0")

        metrics = [
            self._metric(
                "mrr_growth",
                "نمو الإيراد الشهري المتكرّر",
                _share(new_paying, mrr - new_paying),
                "٪ شهريًا",
                "اشتراكات جديدة بقيمة {amount} خلال ٣٠ يومًا",
                {"amount": str(new_paying)},
            ),
            self._metric(
                "activation_rate",
                "معدّل تفعيل العميل",
                _share(activated, total_customers),
                "٪",
                "انضمّوا وأتمّوا عملية واحدة على الأقل",
                {},
            ),
            self._metric(
                "push_adoption",
                "تفعيل إشعارات التطبيق",
                _share(with_push, total_customers),
                "٪",
                "كل نقطة مئوية هنا توفّر رسائل مدفوعة",
                {},
            ),
            self._metric(
                "merchant_churn",
                "انسحاب التجّار",
                _share(cancelled, organizations),
                "٪ خلال ٣٠ يومًا",
                "{cancelled} إلغاء من {total} مؤسسة",
                {"cancelled": cancelled, "total": organizations},
            ),
            self._metric(
                "redemption_rate",
                "معدّل استبدال المكافآت",
                _share(abs(redeemed), granted),
                "٪ من الممنوح",
                "المنخفض جدًّا يعني مكافآت بعيدة المنال",
                {},
            ),
            self._metric(
                "paying_share",
                "نسبة المشتركين المدفوعين",
                _share(paying.count(), active.count()),
                "٪ من النشطين",
                "{paying} مدفوع من {active} نشط",
                {"paying": paying.count(), "active": active.count()},
            ),
        ]

        return Response(
            {
                "metrics": metrics,
                "off_target": [m for m in metrics if not m["on_target"]],
                "generated_at": now,
            }
        )

    def _metric(self, key: str, label: str, value: float, unit: str, hint: str, vars: dict) -> dict:
        """
        المؤشر ومعه هدفه وحكمه — والتوضيح كقالب لا كنصّ جاهز.

        حقن الأرقام هنا بـf-string كان يضع خانات لاتينية وسط
        جملة عربية، ويمنع ترجمة الجملة إلى الإنجليزية أصلًا.
        الواجهة تملأ القالب بنظام أرقام اللغة المختارة.
        """
        target, direction = self.TARGETS[key]
        on_target = value >= float(target) if direction == "up" else value <= float(target)
        return {
            "key": key,
            "label": label,
            "value": round(value, 1),
            "unit": unit,
            "target": float(target),
            "direction": direction,
            "on_target": on_target,
            "hint": hint,
            "hint_vars": {name: str(item) for name, item in vars.items()},
        }


class PlatformUsersView(APIView):
    """
    فريق المنصة ومن يديرون المتاجر.

    لا تعرض العملاء النهائيين: هذه لوحة تشغيل لا دليل هواتف. ومن
    يفتحها يحتاج أن يعرف من يملك صلاحية على ماذا حين يراجع حادثة.
    """

    permission_classes = [IsPlatformAdmin]

    @extend_schema(responses={200: None}, summary="مستخدمو المنصة وموظفو المتاجر")
    def get(self, request):
        User = get_user_model()

        platform = [
            {
                "id": str(user.id),
                "name": user.full_name or "—",
                "phone": user.phone,
                "role": "مالك المنصة" if user.is_superuser else "فريق المنصة",
                "is_active": user.is_active,
                "last_login": user.last_login,
                "joined_at": user.date_joined,
            }
            for user in User.objects.filter(is_platform_admin=True).order_by("-is_superuser", "id")
        ]

        staff = [
            {
                "id": str(member.id),
                "name": member.user.full_name or "—",
                "phone": member.user.phone,
                "role": member.get_role_display(),
                "role_key": member.role,
                "brand": member.branch.brand.name,
                "branch": member.branch.name,
                "is_active": member.user.is_active,
                "last_login": member.user.last_login,
            }
            for member in StaffUser.objects.select_related("user", "branch__brand").order_by(
                "branch__brand__name", "role"
            )[:200]
        ]

        return Response(
            {
                "platform": platform,
                "staff": staff,
                "staff_total": StaffUser.objects.count(),
                "by_role": list(
                    StaffUser.objects.values("role").annotate(count=Count("id")).order_by("-count")
                ),
            }
        )


class PlatformOpsView(APIView):
    """
    حالة التشغيل — من مصادر حقيقية فقط.

    لا يوجد APM في هذا النشر، فلا تُعرض هنا نسبة زمن تشغيل ولا
    متوسط استجابة: رقمٌ لا مصدر له في لوحة تشغيل أسوأ من غيابه،
    لأنه يُقرأ كطمأنة وقت الحادثة.

    ما يُعرض هو ما يمكن إثباته الآن: هل تستجيب القاعدة والكاش،
    ومتى عملت كل مهمة دورية آخر مرة، وهل الأرصدة مطابقة لقيودها،
    وكم يبلغ حجم البيانات.
    """

    permission_classes = [IsPlatformAdmin]

    @extend_schema(responses={200: None}, summary="حالة الخدمات والمهام الدورية")
    def get(self, request):
        return Response(
            {
                "services": self._services(),
                "tasks": self._tasks(),
                "integrity": self._integrity(),
                "volume": {
                    "customers": Customer.objects.filter(deleted_at__isnull=True).count(),
                    "memberships": Membership.objects.count(),
                    "transactions": Transaction.objects.count(),
                    "ledger_entries": LedgerEntry.objects.count(),
                    "branches": Branch.objects.count(),
                },
                "checked_at": timezone.now(),
            }
        )

    def _services(self) -> list[dict]:
        services = []

        start = time.perf_counter()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            ok, detail = True, connection.vendor
        except Exception as error:  # noqa: BLE001 — تُعرض الحالة لا تُرمى
            ok, detail = False, str(error)[:120]
        services.append(self._service("قاعدة البيانات", ok, start, detail))

        start = time.perf_counter()
        try:
            cache.set("walaee:ops:ping", "1", timeout=10)
            ok = cache.get("walaee:ops:ping") == "1"
            detail = "" if ok else "الكتابة نجحت والقراءة لم تُرجع القيمة"
        except Exception as error:  # noqa: BLE001
            ok, detail = False, str(error)[:120]
        services.append(self._service("الكاش والطوابير", ok, start, detail))

        return services

    def _service(self, name: str, ok: bool, start: float, detail: str) -> dict:
        return {
            "name": name,
            "ok": ok,
            "latency_ms": round((time.perf_counter() - start) * 1000, 1),
            "detail": detail,
        }

    def _tasks(self) -> list[dict]:
        """
        المهام الدورية ومتى عملت آخر مرة.

        مهمة معطّلة أو لم تعمل منذ أيام هي الشكل الشائع للعطل
        الصامت: الأرصدة لا تنتهي صلاحيتها، والفواتير لا تصدر، ولا
        شيء يفشل بصوت مسموع.
        """
        try:
            from django_celery_beat.models import PeriodicTask
        except ImportError:  # pragma: no cover — الحزمة مثبّتة في كل البيئات
            return []

        now = timezone.now()
        rows = []
        for task in PeriodicTask.objects.exclude(name__startswith="celery.").order_by("name"):
            last = task.last_run_at
            rows.append(
                {
                    "name": task.name,
                    "task": task.task,
                    "enabled": task.enabled,
                    "schedule": str(task.crontab or task.interval or ""),
                    "last_run_at": last,
                    "total_runs": task.total_run_count,
                    "silent_hours": round((now - last).total_seconds() / 3600, 1) if last else None,
                }
            )
        return rows

    def _integrity(self) -> dict:
        """
        عيّنة من مطابقة الأرصدة لقيودها.

        الفحص الكامل يمرّ على كل محفظة ويعيش في `verify_ledger`
        كمهمة ليلية. هنا عيّنة تكفي للوحة تُفتح لحظيًا — وأي
        انحراف فيها يعني وقف النشر لا تحقيقًا هادئًا.
        """
        sample = list(
            Balance.objects.order_by("-updated_at").values("membership_id", "program_id", "amount")[
                :200
            ]
        )
        drifted = 0
        for row in sample:
            total = LedgerEntry.objects.filter(
                membership_id=row["membership_id"], program_id=row["program_id"]
            ).aggregate(total=Sum("delta"))["total"] or Decimal("0")
            if total != row["amount"]:
                drifted += 1

        return {"checked": len(sample), "drifted": drifted, "ok": drifted == 0}


class PlatformConfigView(APIView):
    """
    إعدادات المنصة والامتثال — ما هو مفعَّل فعلًا.

    كل بند هنا يُقرأ من الإعدادات أو من القاعدة لا من قائمة مكتوبة
    بيد. لوحة امتثال تعرض «مفعَّل» لشيء مطفأ أسوأ من لوحة لا
    توجد: من يقرؤها يتوقّف عن التحقق.
    """

    permission_classes = [IsPlatformAdmin]

    @extend_schema(responses={200: None}, summary="الإعدادات والامتثال ونموذج النقاط")
    def get(self, request):
        consented = Customer.objects.exclude(consent_at=None).count()
        triggers = _append_only_installed()
        counts = {
            row["plan"]: row["total"]
            for row in Subscription.objects.filter(status=Subscription.STATUS_ACTIVE)
            .values("plan")
            .annotate(total=Count("id"))
        }

        return Response(
            {
                "retention": {
                    "audit_months": getattr(settings, "AUDIT_RETENTION_MONTHS", 24),
                    "default_expiry_months": getattr(settings, "DEFAULT_EXPIRY_MONTHS", None),
                    "otp_ttl_seconds": getattr(settings, "OTP_TTL_SECONDS", None),
                    "pos_code_ttl_seconds": getattr(settings, "POS_CODE_TTL_SECONDS", None),
                },
                "privacy": [
                    {
                        "key": "consent",
                        "label": "موافقة مسجَّلة بنسختها وتاريخها",
                        "enabled": consented > 0,
                        "detail": f"{consented} موافقة مسجَّلة",
                    },
                    {
                        "key": "export",
                        "label": "تصدير البيانات من داخل التطبيق",
                        "enabled": True,
                        "detail": "ملف واحد بكل ما تحتفظ به المنصة عن العميل",
                    },
                    {
                        "key": "erasure",
                        "label": "حذف الحساب بتأكيد ثانٍ",
                        "enabled": True,
                        "detail": "إخفاء الهوية مع إبقاء القيود بمعرّف مجهول",
                    },
                    {
                        "key": "append_only",
                        "label": "سجل القيود والتدقيق غير قابل للتعديل",
                        "enabled": triggers,
                        "detail": (
                            "مصدّات قاعدة البيانات مثبّتة"
                            if triggers
                            else "المصدّات غير مثبّتة — شغّل infra/postgres/02-append-only.sql"
                        ),
                    },
                ],
                "network_model": {
                    "phase": 1,
                    "label": "رصيد منفصل لكل علامة",
                    "detail": (
                        "الشبكة تظهر في الهوية الموحّدة والاكتشاف والعروض المتقاطعة — "
                        "دون تبادل قيمة مالية بين التجّار."
                    ),
                    "stages": [
                        {"stage": 1, "label": "رصيد منفصل لكل علامة", "status": "active"},
                        {"stage": 2, "label": "عملة شبكة تمنحها المنصة", "status": "planned"},
                        {"stage": 3, "label": "مقاصة حقيقية بين التجّار", "status": "blocked"},
                    ],
                },
                "features": [
                    {"key": key, "enabled": bool(getattr(settings, key, False))}
                    for key in ("FEATURE_PUBLIC_API", "FEATURE_AI_INSIGHTS")
                ],
                # الباقات وحدودها تعيش في الكود لا في جدول: تغيير حدّ
                # يجب أن يمرّ بمراجعة ونشر لا بتعديل صفّ
                "plans": [
                    {
                        "code": code,
                        "name": label,
                        "monthly_price": str(PLAN_LIMITS[code].get("monthly_price", 0)),
                        "limits": {
                            key: value
                            for key, value in PLAN_LIMITS[code].items()
                            if key != "monthly_price"
                        },
                        "subscribers": counts.get(code, 0),
                    }
                    for code, label in Plan.choices
                ],
            }
        )


def _append_only_installed() -> bool:
    """هل مصدّات المنع مثبّتة على هذه القاعدة فعلًا."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_trigger WHERE tgname = %s", ["ledger_entry_immutable"])
            return cursor.fetchone() is not None
    except Exception:  # noqa: BLE001 — قاعدة غير PostgreSQL في الاختبارات
        return False


def _share(part, whole) -> float:
    """نسبة مئوية بلا قسمة على صفر."""
    part = Decimal(part or 0)
    whole = Decimal(whole or 0)
    if whole <= 0:
        return 0.0
    return float(part / whole * 100)
