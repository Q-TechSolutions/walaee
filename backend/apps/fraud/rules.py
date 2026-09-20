"""
قواعد كشف الشذوذ.

كل قاعدة دالة تأخذ العملية وتُرجع تفاصيل المخالفة أو None. إضافة
قاعدة جديدة = دالة جديدة في RULES بلا لمس محرك التقييم.

تُقيَّم لحظيًا داخل معاملة التأكيد: تأجيلها لمهمة خلفية يعني أن
النمط يُكتشف بعد أن يكون التاجر قد خسر بالفعل.
"""

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from .models import FraudSignal

# عتبات قابلة للضبط لاحقًا من لوحة التاجر
ROUND_AMOUNT_THRESHOLD = Decimal("500")
BURST_WINDOW_MINUTES = 10
BURST_COUNT = 5
HIGH_VALUE_MULTIPLIER = Decimal("10")
REPEAT_CUSTOMER_WINDOW_MINUTES = 3


def rule_same_customer_burst(txn) -> dict | None:
    """نفس العميل عدة مرات على نفس الطرفية خلال دقائق."""
    if txn.customer_id is None:
        return None

    since = timezone.now() - timedelta(minutes=REPEAT_CUSTOMER_WINDOW_MINUTES)
    from apps.ledger.models import Transaction

    count = (
        Transaction.objects.filter(
            terminal_id=txn.terminal_id,
            customer_id=txn.customer_id,
            status=Transaction.STATUS_CONFIRMED,
            created_at__gte=since,
        )
        .exclude(pk=txn.pk)
        .count()
    )

    if count >= 2:
        return {
            "severity": FraudSignal.SEVERITY_MEDIUM,
            "details": {"count": count, "window_minutes": REPEAT_CUSTOMER_WINDOW_MINUTES},
        }
    return None


def rule_cashier_burst(txn) -> dict | None:
    """كاشير واحد يؤكّد عمليات كثيرة في نافذة قصيرة."""
    if txn.staff_user_id is None:
        return None

    since = timezone.now() - timedelta(minutes=BURST_WINDOW_MINUTES)
    from apps.ledger.models import Transaction

    count = Transaction.objects.filter(
        staff_user_id=txn.staff_user_id,
        status=Transaction.STATUS_CONFIRMED,
        created_at__gte=since,
    ).count()

    if count >= BURST_COUNT:
        return {
            "severity": FraudSignal.SEVERITY_MEDIUM,
            "details": {"count": count, "window_minutes": BURST_WINDOW_MINUTES},
        }
    return None


def rule_round_amount(txn) -> dict | None:
    """
    مبلغ مستدير كبير.

    الفواتير الحقيقية نادرًا ما تكون أرقامًا مستديرة تمامًا؛ المبالغ
    المختلَقة غالبًا كذلك.
    """
    amount = txn.invoice_amount
    if amount >= ROUND_AMOUNT_THRESHOLD and amount % Decimal("100") == 0:
        return {
            "severity": FraudSignal.SEVERITY_LOW,
            "details": {"amount": str(amount)},
        }
    return None


def rule_staff_self_transaction(txn) -> dict | None:
    """الكاشير يمنح نقاطًا لرقم هاتفه نفسه."""
    if txn.staff_user_id is None or txn.customer_id is None:
        return None

    if txn.staff_user.user.phone == txn.customer.phone:
        return {
            "severity": FraudSignal.SEVERITY_HIGH,
            "details": {"phone": txn.customer.phone},
        }
    return None


def rule_outlier_amount(txn) -> dict | None:
    """فاتورة أكبر بعشرة أضعاف من متوسط الفرع."""
    from django.db.models import Avg

    from apps.ledger.models import Transaction

    average = (
        Transaction.objects.filter(
            terminal__branch_id=txn.terminal.branch_id,
            status=Transaction.STATUS_CONFIRMED,
        )
        .exclude(pk=txn.pk)
        .aggregate(avg=Avg("invoice_amount"))["avg"]
    )

    # لا حكم قبل وجود تاريخ كافٍ — متوسط مبني على عمليتين بلا معنى
    if average is None or average <= 0:
        return None

    if txn.invoice_amount > Decimal(str(average)) * HIGH_VALUE_MULTIPLIER:
        return {
            "severity": FraudSignal.SEVERITY_HIGH,
            "details": {"amount": str(txn.invoice_amount), "branch_avg": str(round(average, 2))},
        }
    return None


RULES = {
    "same_customer_burst": rule_same_customer_burst,
    "cashier_burst": rule_cashier_burst,
    "round_amount": rule_round_amount,
    "staff_self_transaction": rule_staff_self_transaction,
    "outlier_amount": rule_outlier_amount,
}
