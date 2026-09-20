"""
مهام نقطة البيع.

`rotate_codes` تعمل على طابور `realtime` المعزول: حملة رسائل ضخمة
يجب ألا توقف تدوير رموز الكاشير — docs/architecture/async-tasks.md
"""

import logging

from celery import shared_task
from django.utils import timezone

from apps.tenancy.models import Terminal

from . import codes

logger = logging.getLogger(__name__)


@shared_task(name="apps.pos.tasks.rotate_codes")
def rotate_codes() -> int:
    """يولّد رمزًا جديدًا لكل طرفية نشطة. تعمل كل ٣٠ ثانية."""
    rotated = 0
    now = timezone.now()
    expires = now + timezone.timedelta(seconds=30)

    for terminal in Terminal.objects.filter(is_active=True).only("id"):
        code = codes.issue_code(terminal.id)
        # نسخة للتدقيق فقط — Redis هو المصدر
        Terminal.objects.filter(pk=terminal.pk).update(current_code=code, code_expires_at=expires)
        rotated += 1

    logger.debug("rotated %s terminal codes", rotated)
    return rotated


@shared_task(name="apps.pos.tasks.notify_customer")
def notify_customer(transaction_id: str) -> bool:
    """
    إشعار العميل بعد تأكيد عمليته.

    Web Push هو القناة الافتراضية لأنها مجانية. التنفيذ الفعلي
    يُضاف في المرحلة الثانية مع apps/campaigns.
    """
    logger.info("notify customer for txn=%s", transaction_id)
    return True
