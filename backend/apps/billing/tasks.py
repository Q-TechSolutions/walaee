"""مهام الفوترة — طابور billing."""

import logging

from celery import shared_task
from django.utils import timezone

from .models import Invoice, Subscription
from .services import issue_invoice

logger = logging.getLogger(__name__)

PAST_DUE_GRACE_DAYS = 7


@shared_task(name="apps.billing.tasks.charge_due_subscriptions")
def charge_due_subscriptions() -> int:
    """
    يصدر فواتير الدورات المنتهية. تعمل يوميًا ٠٦:٠٠.

    الإصدار لا يقطع الخدمة: الاشتراك المتأخر يظل يُخدَم، والإيقاف
    قرار بشري. قطع الخدمة آليًا عن متجر تأخرت فاتورته يومًا يعني
    عميلًا واقفًا عند الصندوق لا يحصل على نقاطه.
    """
    now = timezone.now()
    issued = 0

    due = (
        Subscription.objects.filter(current_period_end__lte=now)
        .exclude(status=Subscription.STATUS_CANCELLED)
        .select_related("organization")
    )

    for subscription in due.iterator(chunk_size=100):
        try:
            invoice = issue_invoice(subscription)
            issued += 1
            logger.info("invoice issued %s org=%s", invoice.number, subscription.organization_id)
        except Exception:  # noqa: BLE001 - فشل اشتراك لا يوقف البقية
            logger.exception("invoice failed subscription=%s", subscription.pk)

    return issued


@shared_task(name="apps.billing.tasks.flag_past_due")
def flag_past_due() -> int:
    """يعلّم الاشتراكات التي تجاوزت مهلة السداد."""
    cutoff = timezone.now() - timezone.timedelta(days=PAST_DUE_GRACE_DAYS)

    overdue_ids = (
        Invoice.objects.filter(status=Invoice.STATUS_ISSUED, issued_at__lt=cutoff)
        .values_list("subscription_id", flat=True)
        .distinct()
    )

    updated = Subscription.objects.filter(
        pk__in=list(overdue_ids), status=Subscription.STATUS_ACTIVE
    ).update(status=Subscription.STATUS_PAST_DUE, updated_at=timezone.now())

    if updated:
        logger.warning("%s subscriptions marked past due", updated)
    return updated
