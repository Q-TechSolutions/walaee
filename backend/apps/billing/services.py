"""
منطق الاشتراكات ورصيد الرسائل.

`spend_credits` هي نظير `apply_entry` في عالم الرسائل: المكان الوحيد
الذي يُخصَم فيه رصيد الرسائل، بنفس نمط القفل وبنفس سجل append-only.
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework import status

from apps.common.exceptions import DomainError

from .models import Invoice, MessageCredit, MessageWallet, Plan, Subscription

logger = logging.getLogger(__name__)


class BillingError(DomainError):
    code = "billing_error"
    message = "تعذّر إتمام العملية."


class InsufficientCredits(BillingError):
    code = "insufficient_credits"
    message = "رصيد الرسائل غير كافٍ. اشحن رصيدك قبل الإرسال."
    http_status = status.HTTP_402_PAYMENT_REQUIRED


class PlanLimitReached(BillingError):
    code = "plan_limit_reached"
    message = "بلغت حدّ باقتك الحالية."
    http_status = status.HTTP_402_PAYMENT_REQUIRED


class FeatureNotInPlan(BillingError):
    code = "feature_not_in_plan"
    message = "هذه الميزة غير متاحة في باقتك."
    http_status = status.HTTP_402_PAYMENT_REQUIRED


# ═══════════════════════ الاشتراك ═══════════════════════


def get_subscription(organization) -> Subscription:
    """
    اشتراك المؤسسة، ويُنشأ مجانيًا إن لم يوجد.

    الإنشاء التلقائي مقصود: مؤسسة بلا اشتراك تعني استعلامًا يرجع
    None في كل فحص حدّ، ثم `AttributeError` في مسار حرج.
    """
    subscription = Subscription.objects.filter(organization=organization).first()
    if subscription is not None:
        return subscription

    return Subscription.objects.create(
        organization=organization,
        plan=Plan.FREE,
        status=Subscription.STATUS_TRIAL,
        current_period_end=timezone.now() + timezone.timedelta(days=30),
    )


def check_limit(organization, key: str, current: int) -> None:
    """يرفع PlanLimitReached إذا بلغ العدد الحالي حدّ الباقة."""
    limit = get_subscription(organization).limit(key)
    if limit is None:
        return
    if current >= limit:
        raise PlanLimitReached(
            f"باقتك تسمح بـ {limit} كحد أقصى. رقّ باقتك للمزيد.",
            limit=limit,
            current=current,
        )


def require_feature(organization, key: str) -> None:
    """يرفع FeatureNotInPlan إذا كانت الميزة غير مفعّلة في الباقة."""
    if not get_subscription(organization).limit(key):
        raise FeatureNotInPlan()


# ═══════════════════════ رصيد الرسائل ═══════════════════════


@transaction.atomic
def apply_credit(*, organization, delta: int, reason: str, note: str = "") -> MessageCredit:
    """
    المكان الوحيد الذي يُعدَّل فيه رصيد الرسائل.

    نفس نمط `ledger.apply_entry`: قفل الصف أولًا، ثم القرار، ثم قيد
    غير قابل للتعديل، ثم تحديث اللقطة بـ F().
    """
    if delta == 0:
        raise BillingError("لا تُكتب حركة بمقدار صفر.")

    MessageWallet.objects.get_or_create(organization=organization, defaults={"balance": 0})
    wallet = MessageWallet.objects.select_for_update().get(organization=organization)

    new_balance = wallet.balance + delta
    if new_balance < 0:
        raise InsufficientCredits(available=wallet.balance, requested=-delta)

    credit = MessageCredit.objects.create(
        organization=organization,
        delta=delta,
        reason=reason,
        balance_after=new_balance,
        note=note[:200],
    )

    MessageWallet.objects.filter(pk=wallet.pk).update(
        balance=F("balance") + delta, updated_at=timezone.now()
    )

    logger.info(
        "credit org=%s delta=%s reason=%s balance_after=%s",
        organization.id,
        delta,
        reason,
        new_balance,
    )
    return credit


def spend_credits(*, organization, count: int, note: str = "") -> MessageCredit:
    """يخصم رصيد إرسال. يرفع InsufficientCredits إن لم يكفِ."""
    return apply_credit(
        organization=organization,
        delta=-abs(count),
        reason=MessageCredit.REASON_SEND,
        note=note,
    )


def refund_credits(*, organization, count: int, note: str = "") -> MessageCredit:
    """
    يعيد رصيد رسائل فشل إرسالها.

    الاسترداد إلزامي لا مجاملة: خصم رصيد مقابل رسالة لم تصل هو أخذ
    مال بلا خدمة، ويُكتشف أول ما يراجع التاجر تقريره.
    """
    return apply_credit(
        organization=organization,
        delta=abs(count),
        reason=MessageCredit.REASON_REFUND,
        note=note,
    )


def wallet_balance(organization) -> int:
    wallet = MessageWallet.objects.filter(organization=organization).first()
    return wallet.balance if wallet else 0


def grant_monthly_credits(subscription: Subscription) -> MessageCredit | None:
    """المنحة الشهرية المجانية حسب الباقة."""
    amount = subscription.limit("monthly_free_messages")
    if not amount:
        return None

    return apply_credit(
        organization=subscription.organization,
        delta=amount,
        reason=MessageCredit.REASON_MONTHLY,
        note=f"منحة باقة {subscription.get_plan_display()}",
    )


# ═══════════════════════ الفواتير ═══════════════════════


def _next_invoice_number() -> str:
    """
    ترقيم تسلسلي شهري: WL-YYYYMM-NNNN.

    لا uuid هنا: رقم الفاتورة يُقرأ بصوت عالٍ في مكالمة مع محاسب،
    ويُكتب في تحويل بنكي.
    """
    now = timezone.localtime()
    prefix = f"WL-{now:%Y%m}-"
    last = (
        Invoice.objects.filter(number__startswith=prefix)
        .order_by("-number")
        .values_list("number", flat=True)
        .first()
    )
    sequence = int(last.rsplit("-", 1)[1]) + 1 if last else 1
    return f"{prefix}{sequence:04d}"


@transaction.atomic
def issue_invoice(subscription: Subscription) -> Invoice:
    """يصدر فاتورة الدورة الحالية ويدفع الاشتراك للدورة التالية."""
    amount = Decimal(subscription.limit("monthly_price"))

    invoice = Invoice.objects.create(
        subscription=subscription,
        number=_next_invoice_number(),
        amount=amount,
        status=Invoice.STATUS_ISSUED,
        period_start=subscription.current_period_start,
        period_end=subscription.current_period_end,
        issued_at=timezone.now(),
    )

    subscription.current_period_start = subscription.current_period_end
    subscription.current_period_end = subscription.current_period_end + timezone.timedelta(days=30)
    subscription.mrr = amount
    subscription.save(
        update_fields=["current_period_start", "current_period_end", "mrr", "updated_at"]
    )

    grant_monthly_credits(subscription)
    return invoice


@transaction.atomic
def mark_invoice_paid(invoice: Invoice, *, reference: str = "") -> Invoice:
    """يسجّل سداد فاتورة ويعيد الاشتراك إلى الحالة النشطة."""
    if invoice.status == Invoice.STATUS_PAID:
        raise BillingError("هذه الفاتورة مسدّدة بالفعل.", code="already_paid")

    invoice.status = Invoice.STATUS_PAID
    invoice.paid_at = timezone.now()
    invoice.payment_ref = reference[:120]
    invoice.save(update_fields=["status", "paid_at", "payment_ref", "updated_at"])

    subscription = invoice.subscription
    if subscription.status in (Subscription.STATUS_TRIAL, Subscription.STATUS_PAST_DUE):
        subscription.status = Subscription.STATUS_ACTIVE
        subscription.save(update_fields=["status", "updated_at"])

    return invoice
