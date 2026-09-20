"""
مهام محرك القيود.

`expire_balances` تكتب قيدًا بـ `reason=expire` لا تصفّر الرصيد
مباشرة: انتهاء الصلاحية حدث مالي يجب أن يظهر في كشف حساب العميل،
وإلا اختفت نقاطه بلا تفسير.

المرجع: docs/architecture/async-tasks.md
"""

import logging
from decimal import Decimal

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.loyalty.models import Balance

from .models import LedgerEntry
from .services import apply_entry

logger = logging.getLogger(__name__)

EXPIRY_WARNING_DAYS = 30


@shared_task(name="apps.ledger.tasks.expire_balances")
def expire_balances() -> int:
    """يصفّر الأرصدة المنتهية بقيد صريح. تعمل يوميًا ٠٣:٠٠."""
    now = timezone.now()
    expired = 0

    candidates = Balance.objects.filter(expires_at__lte=now, amount__gt=0).select_related(
        "membership", "program__rule"
    )

    for balance in candidates.iterator(chunk_size=200):
        try:
            with transaction.atomic():
                # القراءة داخل المعاملة: الرصيد قد يكون تغيّر بين
                # بناء القائمة ومعالجة هذا الصف
                current = Balance.objects.select_for_update().get(pk=balance.pk)
                if current.amount <= 0 or current.expires_at > now:
                    continue

                apply_entry(
                    membership=current.membership,
                    program=current.program,
                    delta=-current.amount,
                    reason=LedgerEntry.REASON_EXPIRE,
                )
                expired += 1
        except Exception:  # noqa: BLE001 - فشل رصيد لا يوقف البقية
            logger.exception("expire failed balance=%s", balance.pk)

    logger.info("expired %s balances", expired)
    return expired


@shared_task(name="apps.ledger.tasks.notify_expiring")
def notify_expiring() -> int:
    """
    تنبيه مجاني قبل انتهاء الرصيد بثلاثين يومًا.

    على القناة المجانية فقط: تنبيه خدمي يخصم رصيدًا مدفوعًا من
    التاجر بلا أن يطلبه هو فاتورة مفاجئة.
    """
    from apps.campaigns.services import notify_one

    now = timezone.now()
    window_start = now + timezone.timedelta(days=EXPIRY_WARNING_DAYS - 1)
    window_end = now + timezone.timedelta(days=EXPIRY_WARNING_DAYS)

    notified = 0
    candidates = Balance.objects.filter(
        expires_at__gte=window_start, expires_at__lt=window_end, amount__gt=0
    ).select_related("membership__customer", "membership__brand", "program")

    for balance in candidates.iterator(chunk_size=200):
        customer = balance.membership.customer
        if customer.deleted_at is not None:
            continue

        body = (
            f"رصيدك في {balance.membership.brand.name}: "
            f"{balance.amount} {balance.program.unit_label} "
            f"تنتهي خلال {EXPIRY_WARNING_DAYS} يومًا. استبدلها قبل فوات الأوان."
        )
        if notify_one(customer=customer, brand=balance.membership.brand, body=body):
            notified += 1

    logger.info("notified %s customers about expiring balances", notified)
    return notified


@shared_task(name="apps.ledger.tasks.verify_integrity")
def verify_integrity() -> dict:
    """
    يقارن كل لقطة رصيد بمجموع قيودها.

    أي اختلاف يعني مسارًا يكتب في الرصيد خارج المحرك — وهو عطل
    يستوجب وقف النشر. المهمة تشتغل يوميًا وتسجّل النتيجة بمستوى
    ERROR حتى تظهر في التنبيهات لا في سجل يقرأه أحد بعد شهر.
    """
    from django.db.models import Sum

    drifted = []
    checked = 0

    for balance in Balance.objects.select_related("membership", "program").iterator(chunk_size=500):
        checked += 1
        total = LedgerEntry.objects.filter(
            membership_id=balance.membership_id, program_id=balance.program_id
        ).aggregate(total=Sum("delta"))["total"] or Decimal("0")

        if total != balance.amount:
            drifted.append(
                {
                    "balance_id": str(balance.pk),
                    "snapshot": str(balance.amount),
                    "ledger_total": str(total),
                }
            )

    if drifted:
        logger.error("balance drift detected: %s of %s", len(drifted), checked)
    else:
        logger.info("balance integrity ok: %s checked", checked)

    return {"checked": checked, "drifted": len(drifted), "details": drifted[:20]}
