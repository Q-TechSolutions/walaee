"""
منطق الحملات.

الترتيب في `send_campaign` مقصود بالكامل:
  ١) قفل الحملة — يمنع إرسالها مرتين بضغطتين متزامنتين.
  ٢) بناء صفوف الرسائل أولًا بقيد فريد على (حملة، عميل).
  ٣) خصم الرصيد مرة واحدة للحملة كلها لا لكل رسالة.
  ٤) الإرسال الفعلي، واسترداد رصيد ما فشل.

خصم الرصيد قبل الإرسال مقصود: الخصم بعده يعني أن انقطاعًا في
منتصف الحملة يترك رسائل أُرسلت بلا خصم.
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.billing import services as billing
from apps.common.exceptions import DomainError, InvalidState

from . import router, segments
from .models import Campaign, Channel, MessageJob
from .providers import get_channel_provider

logger = logging.getLogger(__name__)


class CampaignError(DomainError):
    code = "campaign_error"
    message = "تعذّر تنفيذ الحملة."


@transaction.atomic
def create_campaign(
    *,
    brand,
    staff_user,
    name: str,
    message_template: str,
    segment_query: dict,
    channel_priority: list[str] | None = None,
    scheduled_at=None,
) -> tuple[Campaign, router.Estimate]:
    """
    ينشئ حملة ويُرجع تقديرها.

    التقدير جزء من الإنشاء لا خطوة منفصلة: حملة مسودة بلا رقم تكلفة
    هي بالضبط ما نحاول منعه.
    """
    billing.require_feature(brand.organization, "campaigns_enabled")

    try:
        cleaned_segment = segments.validate(segment_query or {})
    except segments.InvalidSegment as exc:
        raise CampaignError(str(exc), code="invalid_segment") from exc

    campaign = Campaign(
        brand=brand,
        created_by=staff_user,
        name=name.strip()[:140],
        message_template=message_template.strip(),
        segment_query=cleaned_segment,
        channel_priority=channel_priority or [],
        scheduled_at=scheduled_at,
        status=Campaign.STATUS_SCHEDULED if scheduled_at else Campaign.STATUS_DRAFT,
    )

    memberships = segments.resolve(brand, cleaned_segment)
    quote = router.estimate(memberships, campaign.channels)

    campaign.estimated_recipients = quote.reachable
    campaign.estimated_cost = quote.cost
    campaign.save()

    return campaign, quote


def preview(brand, segment_query: dict, channel_priority: list[str] | None = None) -> dict:
    """تقدير بلا إنشاء — يُستدعى وهو يعدّل الشريحة في الواجهة."""
    try:
        cleaned = segments.validate(segment_query or {})
    except segments.InvalidSegment as exc:
        raise CampaignError(str(exc), code="invalid_segment") from exc

    memberships = segments.resolve(brand, cleaned)
    quote = router.estimate(memberships, channel_priority or router.DEFAULT_PRIORITY)

    return {
        **quote.as_dict(),
        "segment_description": segments.describe(cleaned),
        "wallet_balance": billing.wallet_balance(brand.organization),
    }


@transaction.atomic
def _lock_and_build_jobs(campaign_id) -> tuple[Campaign, list[MessageJob]]:
    """يقفل الحملة ويبني صفوف الرسائل. يُرجع الحملة والصفوف."""
    campaign = (
        Campaign.objects.select_for_update(of=("self",))
        .select_related("brand__organization")
        .get(pk=campaign_id)
    )

    if campaign.status in (Campaign.STATUS_SENDING, Campaign.STATUS_SENT):
        raise InvalidState("هذه الحملة أُرسلت بالفعل.", code="already_sent")
    if campaign.status == Campaign.STATUS_CANCELLED:
        raise InvalidState("هذه الحملة ملغاة.", code="cancelled")

    memberships = segments.resolve(campaign.brand, campaign.segment_query)

    jobs = []
    for membership in memberships.select_related("customer").iterator(chunk_size=500):
        route = router.pick_channel(membership.customer, campaign.channels)
        if not route.reachable:
            continue
        jobs.append(
            MessageJob(
                campaign=campaign,
                customer=membership.customer,
                channel=route.channel,
                cost=route.cost,
                status=MessageJob.STATUS_QUEUED,
            )
        )

    # ignore_conflicts يجعل إعادة تشغيل مهمة فشلت في منتصفها آمنة:
    # القيد الفريد على (حملة، عميل) يبتلع المكرر بدل أن يُسقِط كل شيء
    MessageJob.objects.bulk_create(jobs, batch_size=500, ignore_conflicts=True)

    billable = sum(1 for job in jobs if job.cost > 0)
    if billable:
        billing.spend_credits(
            organization=campaign.brand.organization,
            count=billable,
            note=f"حملة: {campaign.name}"[:200],
        )

    campaign.status = Campaign.STATUS_SENDING
    campaign.started_at = timezone.now()
    campaign.save(update_fields=["status", "started_at", "updated_at"])

    return campaign, jobs


def send_campaign(campaign_id) -> dict:
    """
    ينفّذ الحملة.

    الإرسال خارج المعاملة: معاملة مفتوحة طوال آلاف النداءات الشبكية
    تقفل صفوفًا لدقائق وتخنق قاعدة البيانات.
    """
    campaign, _ = _lock_and_build_jobs(campaign_id)

    sent = failed = 0
    refundable = 0
    actual_cost = Decimal("0")

    queued = MessageJob.objects.filter(
        campaign=campaign, status=MessageJob.STATUS_QUEUED
    ).select_related("customer")

    for job in queued.iterator(chunk_size=200):
        body = router.render(
            campaign.message_template,
            customer=job.customer,
            brand=campaign.brand,
        )
        try:
            provider = get_channel_provider(job.channel)
            result = provider.send(phone=job.customer.phone, body=body)
        except Exception as exc:  # noqa: BLE001 - فشل مزوّد لا يُسقِط الحملة
            job.status = MessageJob.STATUS_FAILED
            job.error = str(exc)[:255]
            job.save(update_fields=["status", "error", "updated_at"])
            failed += 1
            if job.cost > 0:
                refundable += 1
            logger.warning("message failed job=%s channel=%s", job.id, job.channel)
            continue

        job.status = MessageJob.STATUS_SENT
        job.provider_msg_id = (result.provider_msg_id or "")[:120]
        job.sent_at = timezone.now()
        job.save(update_fields=["status", "provider_msg_id", "sent_at", "updated_at"])
        sent += 1
        actual_cost += job.cost

    if refundable:
        billing.refund_credits(
            organization=campaign.brand.organization,
            count=refundable,
            note=f"استرداد رسائل فاشلة: {campaign.name}"[:200],
        )

    campaign.status = Campaign.STATUS_SENT if sent or not failed else Campaign.STATUS_FAILED
    campaign.finished_at = timezone.now()
    campaign.actual_cost = actual_cost
    campaign.save(update_fields=["status", "finished_at", "actual_cost", "updated_at"])

    logger.info("campaign sent=%s failed=%s cost=%s id=%s", sent, failed, actual_cost, campaign.id)
    return {"sent": sent, "failed": failed, "refunded": refundable, "cost": str(actual_cost)}


@transaction.atomic
def cancel_campaign(campaign_id, *, staff_user=None) -> Campaign:
    """يلغي حملة لم تبدأ بعد."""
    campaign = Campaign.objects.select_for_update(of=("self",)).get(pk=campaign_id)

    if not campaign.is_editable:
        raise InvalidState("لا يمكن إلغاء حملة بدأ إرسالها.", code="not_cancellable")

    campaign.status = Campaign.STATUS_CANCELLED
    campaign.save(update_fields=["status", "updated_at"])
    return campaign


def notify_one(*, customer, brand, body: str, channel: str = Channel.PUSH) -> bool:
    """
    رسالة تشغيلية واحدة خارج الحملات — مثل تنبيه انتهاء الرصيد.

    تُرسَل على القناة المجانية فقط. تنبيه خدمي يخصم رصيدًا مدفوعًا
    بلا أن يطلبه التاجر هو فاتورة مفاجئة.
    """
    route = router.pick_channel(customer, [channel])
    if not route.reachable or route.cost > 0:
        return False

    try:
        get_channel_provider(route.channel).send(phone=customer.phone, body=body)
        return True
    except Exception:  # noqa: BLE001
        logger.warning("notify failed customer=%s brand=%s", customer.id, brand.id)
        return False
