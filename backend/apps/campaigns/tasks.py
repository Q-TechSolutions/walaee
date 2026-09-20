"""مهام الحملات — طابور messaging المعزول."""

import logging

from celery import shared_task
from django.utils import timezone

from .models import Campaign

logger = logging.getLogger(__name__)


@shared_task(name="apps.campaigns.tasks.send_campaign_task", bind=True, max_retries=2)
def send_campaign_task(self, campaign_id: str) -> dict:
    """ينفّذ حملة. إعادة المحاولة آمنة بفضل القيد الفريد على المستلم."""
    from .services import send_campaign

    try:
        return send_campaign(campaign_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("campaign send failed id=%s", campaign_id)
        raise self.retry(exc=exc, countdown=60) from exc


@shared_task(name="apps.campaigns.tasks.dispatch_scheduled")
def dispatch_scheduled() -> int:
    """
    يطلق الحملات التي حان موعدها.

    تعمل كل خمس دقائق. الدقة بالدقيقة غير مطلوبة هنا، ومحاولة
    تحقيقها تعني مهمة تعمل كل ثانية بلا فائدة.
    """
    due = Campaign.objects.filter(
        status=Campaign.STATUS_SCHEDULED, scheduled_at__lte=timezone.now()
    ).values_list("id", flat=True)

    count = 0
    for campaign_id in due:
        send_campaign_task.delay(str(campaign_id))
        count += 1

    if count:
        logger.info("dispatched %s scheduled campaigns", count)
    return count
