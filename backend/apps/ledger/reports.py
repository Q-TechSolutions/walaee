"""
مؤشرات لوحة التاجر والتقارير.

المؤشر الأهم هو **الالتزام القائم**: قيمة النقاط الممنوحة وغير
المستبدَلة بعد، مقوّمة بتكلفتها الفعلية على التاجر لا بعددها.

سبب أهميته: النقطة ليست رقمًا في شاشة، هي وعد بخصم مستقبلي. تاجر
لا يعرف حجم هذا الوعد يكتشفه دفعة واحدة حين يأتي العملاء ليصرفوه.
أول سؤال يسأله محاسب التاجر هو هذا الرقم، وقابليته للدفاع عنه هي
سبب كون `LedgerEntry` غير قابل للتعديل.
"""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.accounts.models import Customer
from apps.loyalty.models import Balance, LoyaltyProgram, Membership, Reward

from .models import LedgerEntry, Redemption, Transaction


def outstanding_liability(brand) -> dict:
    """
    الالتزام القائم بالوحدات وبالجنيه.

    التقويم بالجنيه يحتاج سعر الوحدة، ويُشتق من أرخص مكافأة في كل
    برنامج: تكلفتها على التاجر مقسومة على عدد الوحدات المطلوبة.
    هذا أقرب تقدير متاح، وهو متحفّظ عمدًا — الرقم المتفائل في
    التزام مالي يضرّ أكثر مما ينفع.
    """
    programs = LoyaltyProgram.objects.filter(brand=brand, is_active=True)
    breakdown = []
    total_units = Decimal("0")
    total_value = Decimal("0")

    for program in programs:
        units = Balance.objects.filter(program=program).aggregate(total=Sum("amount"))[
            "total"
        ] or Decimal("0")

        unit_value = _unit_value(program)
        value = (units * unit_value).quantize(Decimal("0.01"))

        breakdown.append(
            {
                "program_id": str(program.id),
                "program_name": program.name,
                "type": program.type,
                "unit_label": program.unit_label,
                "outstanding_units": str(units),
                "unit_value": str(unit_value),
                "estimated_value": str(value),
            }
        )
        total_units += units
        total_value += value

    return {
        "total_units": str(total_units),
        "estimated_value": str(total_value),
        "currency": "EGP",
        "by_program": breakdown,
        "note": ("القيمة مقدَّرة بتكلفة أرخص مكافأة في كل برنامج. " "الرقم متحفّظ عمدًا."),
    }


def _unit_value(program) -> Decimal:
    """تكلفة الوحدة الواحدة على التاجر."""
    cheapest = (
        Reward.objects.filter(program=program, is_active=True, cost_amount__gt=0)
        .order_by("cost_amount")
        .first()
    )
    if cheapest is None or not cheapest.merchant_cost:
        return Decimal("0")
    return (cheapest.merchant_cost / cheapest.cost_amount).quantize(Decimal("0.0001"))


def dashboard(brand, *, days: int = 30) -> dict:
    """المؤشرات الستة التي يراها التاجر أول ما يفتح لوحته."""
    since = timezone.now() - timedelta(days=days)
    previous_since = since - timedelta(days=days)

    txns = Transaction.objects.filter(
        terminal__branch__brand=brand, status=Transaction.STATUS_CONFIRMED
    )
    current = txns.filter(created_at__gte=since)
    previous = txns.filter(created_at__gte=previous_since, created_at__lt=since)

    current_stats = current.aggregate(
        count=Count("id"), revenue=Sum("invoice_amount"), avg=Avg("invoice_amount")
    )
    previous_stats = previous.aggregate(count=Count("id"), revenue=Sum("invoice_amount"))

    members = Membership.objects.filter(brand=brand, customer__deleted_at__isnull=True)
    new_members = members.filter(joined_at__gte=since).count()

    redemptions = Redemption.objects.filter(
        membership__brand=brand, status=Redemption.STATUS_USED, used_at__gte=since
    ).count()

    # العميل العائد هو من أتمّ أكثر من عملية في الفترة — وهو المؤشر
    # الوحيد الذي يقيس ما بُني البرنامج من أجله أصلًا
    repeat = current.values("customer_id").annotate(visits=Count("id")).filter(visits__gt=1).count()
    active_customers = current.values("customer_id").distinct().count()

    return {
        "period_days": days,
        "transactions": {
            "count": current_stats["count"] or 0,
            "change_pct": _change(current_stats["count"], previous_stats["count"]),
        },
        "revenue": {
            "total": str(current_stats["revenue"] or Decimal("0")),
            "average_invoice": str(
                (current_stats["avg"] or Decimal("0")).quantize(Decimal("0.01"))
            ),
            "change_pct": _change(current_stats["revenue"], previous_stats["revenue"]),
        },
        "customers": {
            "total": members.count(),
            "new": new_members,
            "active": active_customers,
            "repeat": repeat,
            "repeat_rate_pct": _pct(repeat, active_customers),
        },
        "redemptions": redemptions,
        "liability": outstanding_liability(brand),
        "open_fraud_signals": _open_signals(brand),
    }


def _open_signals(brand) -> int:
    from apps.fraud.models import FraudSignal

    return FraudSignal.objects.filter(
        transaction__terminal__branch__brand=brand, status=FraudSignal.STATUS_OPEN
    ).count()


def _change(current, previous) -> float | None:
    """نسبة التغيّر. None حين لا توجد فترة سابقة يُقاس عليها."""
    current = Decimal(current or 0)
    previous = Decimal(previous or 0)
    if previous == 0:
        return None
    return float(((current - previous) / previous * 100).quantize(Decimal("0.1")))


def _pct(part, whole) -> float:
    if not whole:
        return 0.0
    return float((Decimal(part) / Decimal(whole) * 100).quantize(Decimal("0.1")))


def daily_series(brand, *, days: int = 30) -> list[dict]:
    """
    سلسلة يومية للرسم البياني — **يوم لكل يوم في المدى**.

    الأيام الفارغة تُرجَع أصفارًا لا تُحذف. الحذف يبدو توفيرًا وهو
    تزوير للشكل: أربع عمليات في أربعة أيام متفرّقة من الشهر كانت
    تُرسَم كخطّ صاعد متّصل لا يُفرَّق عن أربع عمليات في أربعة أيام
    متتالية. والأسوأ أن متجرًا بيوم نشاط واحد كان يعطي نقطة واحدة،
    فيرسم الخط مثلّثًا لا معنى له بدل أن يقول «يوم واحد».

    المدى يُحسَب بالتقويم المحلي (`Africa/Cairo`): «آخر ٣٠ يومًا»
    لصاحب المتجر تعني ثلاثين يومًا تقويميًا تنتهي اليوم، لا ٧٢٠
    ساعة تبدأ من لحظة فتح الصفحة — وإلا تغيّر أول عمود كلما حُدِّثت
    اللوحة.
    """
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)

    rows = (
        Transaction.objects.filter(
            terminal__branch__brand=brand,
            status=Transaction.STATUS_CONFIRMED,
            created_at__date__gte=start,
        )
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"), revenue=Sum("invoice_amount"))
    )

    found = {
        row["day"]: (row["count"], row["revenue"] or Decimal("0"))
        for row in rows
        if row["day"] is not None
    }

    series = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        count, revenue = found.get(day, (0, Decimal("0")))
        series.append(
            {
                "date": day.isoformat(),
                "transactions": count,
                "revenue": str(revenue),
            }
        )
    return series


def customer_segments(brand) -> dict:
    """
    توزيع العملاء على شرائح سلوكية.

    الشرائح هي نفسها التي تُستخدم في استهداف الحملات، فيرى التاجر
    الرقم ثم يبني عليه حملة مباشرة بلا إعادة تعريف.
    """
    now = timezone.now()
    members = Membership.objects.filter(brand=brand, customer__deleted_at__isnull=True)

    # استعلام منفصل لكل نافذة أوضح — وأسرع — من annotate مركّب
    # يجمع كل القيود ثم يصفّيها في بايثون
    entries = LedgerEntry.objects.filter(membership__brand=brand)

    def _active_since(days):
        cutoff = now - timedelta(days=days)
        return entries.filter(created_at__gte=cutoff).values("membership_id").distinct().count()

    total = members.count()
    active_30 = _active_since(30)
    active_90 = _active_since(90)

    return {
        "total": total,
        "active_30d": active_30,
        "active_90d": active_90,
        "dormant_90d": max(0, total - active_90),
        "new_7d": members.filter(joined_at__gte=now - timedelta(days=7)).count(),
        "with_consent": Customer.objects.filter(
            memberships__brand=brand, consent_at__isnull=False, deleted_at__isnull=True
        )
        .distinct()
        .count(),
    }


def top_customers(brand, *, limit: int = 20) -> list[dict]:
    """أعلى العملاء إنفاقًا — يُستخدم في برامج المستويات."""
    rows = (
        Transaction.objects.filter(
            terminal__branch__brand=brand,
            status=Transaction.STATUS_CONFIRMED,
            customer__isnull=False,
        )
        .values("customer_id", "customer__phone", "customer__full_name")
        .annotate(visits=Count("id"), spend=Sum("invoice_amount"))
        .order_by("-spend")[:limit]
    )

    return [
        {
            "customer_id": str(row["customer_id"]),
            "phone": row["customer__phone"],
            "name": row["customer__full_name"],
            "visits": row["visits"],
            "total_spend": str(row["spend"] or Decimal("0")),
        }
        for row in rows
    ]


def branch_performance(brand) -> list[dict]:
    """مقارنة الفروع — يكشف الفرع الذي لا يطبّق البرنامج."""
    rows = (
        Transaction.objects.filter(
            terminal__branch__brand=brand, status=Transaction.STATUS_CONFIRMED
        )
        .values("terminal__branch_id", "terminal__branch__name")
        .annotate(
            count=Count("id"),
            revenue=Sum("invoice_amount"),
            customers=Count("customer_id", distinct=True),
        )
        .order_by("-revenue")
    )

    return [
        {
            "branch_id": str(row["terminal__branch_id"]),
            "branch_name": row["terminal__branch__name"],
            "transactions": row["count"],
            "revenue": str(row["revenue"] or Decimal("0")),
            "customers": row["customers"],
        }
        for row in rows
    ]


def program_performance(brand) -> list[dict]:
    """أداء كل برنامج: الممنوح مقابل المستبدَل."""
    result = []
    for program in LoyaltyProgram.objects.filter(brand=brand):
        stats = LedgerEntry.objects.filter(program=program).aggregate(
            granted=Sum("delta", filter=Q(delta__gt=0)),
            redeemed=Sum("delta", filter=Q(reason=LedgerEntry.REASON_REDEEM)),
            expired=Sum("delta", filter=Q(reason=LedgerEntry.REASON_EXPIRE)),
        )
        granted = stats["granted"] or Decimal("0")
        redeemed = abs(stats["redeemed"] or Decimal("0"))

        result.append(
            {
                "program_id": str(program.id),
                "name": program.name,
                "type": program.type,
                "granted": str(granted),
                "redeemed": str(redeemed),
                "expired": str(abs(stats["expired"] or Decimal("0"))),
                # معدل الاستبدال المنخفض جدًّا ليس ربحًا للتاجر:
                # يعني أن المكافأة بعيدة المنال فالبرنامج لا يحفّز أحدًا
                "redemption_rate_pct": _pct(redeemed, granted),
            }
        )
    return result


def recent_activity(brand, *, limit: int = 12) -> list[dict]:
    """
    آخر ما حدث على نقاط البيع — عمليات واستبدالات معًا.

    الاثنان في تدفّق واحد مرتَّب زمنيًا لا في جدولين: من يفتح هذه
    الشاشة يسأل «إيه اللي بيحصل عند الصندوق دلوقتي؟»، وفصل المنح
    عن الصرف يجبره على قراءة جدولين ودمجهما في رأسه.

    يُعرَض اسم الكاشير لأن المساءلة نصف الغرض: رقم بلا اسم لا
    يكشف نمطًا، والنمط هو ما يُكتشَف به الاستغلال الداخلي.
    """
    rows = (
        Transaction.objects.filter(terminal__branch__brand=brand)
        .select_related("customer", "terminal__branch", "staff_user__user")
        .prefetch_related("entries")
        .order_by("-created_at")[:limit]
    )

    activity = []
    for txn in rows:
        # مجموع أثر العملية على الأرصدة — قد يكون قيدين (ترحيب + منح)
        delta = sum((entry.delta for entry in txn.entries.all()), Decimal("0"))

        activity.append(
            {
                "id": str(txn.id),
                "kind": "transaction",
                "at": txn.created_at,
                "customer": (
                    txn.customer.full_name or "عميل بلا اسم" if txn.customer_id else "زائر جديد"
                ),
                "branch": txn.terminal.branch.name,
                "cashier": (
                    txn.staff_user.user.full_name
                    if txn.staff_user_id and txn.staff_user.user_id
                    else "—"
                ),
                "amount": str(txn.invoice_amount),
                "delta": str(delta),
                "status": txn.status,
            }
        )
    return activity


def cashier_shift(staff) -> dict:
    """
    ما أنجزه هذا الكاشير اليوم.

    بتقويم محلي لا بآخر ٢٤ ساعة: «عمليات اليوم» عند من يقف خلف
    الصندوق تعني ورديته، ونافذة متحرّكة تجعل الرقم يتغيّر كلما
    حُدّثت الشاشة بلا سبب مفهوم.
    """
    today = timezone.localdate()
    rows = Transaction.objects.filter(
        staff_user=staff,
        status=Transaction.STATUS_CONFIRMED,
        created_at__date=today,
    )

    return {
        "transactions": rows.count(),
        "revenue": str(rows.aggregate(total=Sum("invoice_amount"))["total"] or Decimal("0")),
        "customers": rows.values("customer_id").distinct().count(),
    }


def reward_usage(brand) -> dict[str, int]:
    """
    كم مرة صُرفت كل مكافأة فعلًا، مفهرسة بمعرّفها.

    المصروفة وحدها (`used`) لا المُصدَرة: كود أُصدر وانتهت صلاحيته
    بلا استعمال ليس استبدالًا، وعدّه يجعل المكافأة تبدو رائجة وهي
    لم تُستلَم قط.
    """
    rows = (
        Redemption.objects.filter(
            reward__program__brand=brand,
            status=Redemption.STATUS_USED,
        )
        .values("reward_id")
        .annotate(count=Count("id"))
    )
    return {str(row["reward_id"]): row["count"] for row in rows}
