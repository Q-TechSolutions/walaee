"""
محرك القيود — المكان الوحيد في المشروع الذي يُعدَّل فيه الرصيد.

لا يوجد في قاعدة الكود كلها سطر آخر يكتب في `loyalty.Balance`.
أي مسار جديد يحتاج تعديل رصيد يستدعي `apply_entry` — بلا استثناء.

تغطية الاختبارات هنا ١٠٠٪ إلزامية وشرط للدمج.
المرجع: docs/architecture/README.md و docs/architecture/testing.md
"""

import logging
import secrets
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone
from rest_framework import status

from apps.common.exceptions import DomainError
from apps.loyalty.models import Balance, Membership
from apps.loyalty.rules import compute_expiry

from .models import LedgerEntry, Redemption

logger = logging.getLogger(__name__)


# ═══════════════════════ أخطاء المجال ═══════════════════════


class LedgerError(DomainError):
    code = "ledger_error"
    message = "تعذّر تنفيذ الحركة على الرصيد."


class DailyCapExceeded(LedgerError):
    code = "daily_cap_exceeded"
    message = "تم بلوغ السقف اليومي لهذا العميل في هذا البرنامج."
    http_status = status.HTTP_422_UNPROCESSABLE_ENTITY


class InsufficientBalance(LedgerError):
    code = "insufficient_balance"
    message = "الرصيد غير كافٍ لإتمام هذه العملية."
    http_status = status.HTTP_422_UNPROCESSABLE_ENTITY


class AlreadyReversed(LedgerError):
    code = "already_reversed"
    message = "هذا القيد معكوس بالفعل."
    http_status = status.HTTP_409_CONFLICT


class MembershipBlocked(LedgerError):
    code = "membership_blocked"
    message = "هذه العضوية محظورة."
    http_status = status.HTTP_403_FORBIDDEN


# ═══════════════════════ المحرك ═══════════════════════


@transaction.atomic
def apply_entry(
    *,
    membership: Membership,
    program,
    delta: Decimal,
    reason: str,
    transaction_obj=None,
    reverses: LedgerEntry | None = None,
    actor=None,
) -> LedgerEntry:
    """
    يكتب قيدًا ويحدّث لقطة الرصيد — ذرّيًا ومقاومًا للتزامن.

    الترتيب هنا مقصود بالكامل:
      ١) قفل صف الرصيد أولًا قبل أي قراءة يُبنى عليها قرار.
      ٢) فحص السقف بعد القفل — قبله يكون الفحص على بيانات قديمة.
      ٣) منع السالب.
      ٤) كتابة القيد.
      ٥) تحديث اللقطة بـ F() لا بقيمة محسوبة في بايثون.
      ٦) سجل تدقيق.
    """
    delta = Decimal(delta)
    if delta == 0:
        raise LedgerError("لا يُكتب قيد بمقدار صفر.")

    if membership.status == Membership.STATUS_BLOCKED:
        raise MembershipBlocked()

    # ── ١) قفل صف الرصيد — يُسلسِل كل الحركات على نفس المحفظة ──
    # get_or_create ثم select_for_update في استعلامين منفصلين يترك
    # فجوة سباق؛ لذلك يُنشأ الصف أولًا ثم يُقفل صراحةً.
    Balance.objects.get_or_create(
        membership=membership, program=program, defaults={"amount": Decimal("0")}
    )
    balance = Balance.objects.select_for_update().get(membership=membership, program=program)

    rule = program.rule

    # ── ٢) السقف اليومي ──
    if delta > 0 and rule.max_per_day is not None:
        earned_today = LedgerEntry.objects.filter(
            membership=membership,
            program=program,
            reason=LedgerEntry.REASON_EARN,
            created_at__date=timezone.localdate(),
        ).aggregate(total=Sum("delta"))["total"] or Decimal("0")

        if earned_today + delta > rule.max_per_day:
            raise DailyCapExceeded(earned_today=str(earned_today), cap=str(rule.max_per_day))

    # ── ٣) منع الرصيد السالب ──
    new_amount = balance.amount + delta
    if new_amount < 0:
        raise InsufficientBalance(available=str(balance.amount), requested=str(-delta))

    # ── ٤) القيد — إضافة فقط ──
    entry = LedgerEntry.objects.create(
        membership=membership,
        program=program,
        delta=delta,
        reason=reason,
        transaction=transaction_obj,
        reverses=reverses,
        balance_after=new_amount,
        actor_label=str(actor) if actor else "",
    )

    # ── ٥) تحديث اللقطة على مستوى قاعدة البيانات ──
    # F() يجعل الجمع يحدث داخل القاعدة لا في بايثون: لو تسلّلت حركة
    # أخرى رغم القفل، النتيجة تبقى صحيحة حسابيًا.
    Balance.objects.filter(pk=balance.pk).update(
        amount=F("amount") + delta,
        expires_at=compute_expiry(rule) if delta > 0 else balance.expires_at,
        updated_at=timezone.now(),
    )

    # ── ٦) سجل تدقيق غير قابل للحذف ──
    from apps.audit.models import AuditLog

    AuditLog.record(
        actor=actor,
        action=f"ledger.{reason}",
        entity=entry,
        after={
            "delta": str(delta),
            "balance_after": str(new_amount),
            "program": str(program.id),
        },
    )

    logger.info(
        "ledger entry=%s membership=%s delta=%s reason=%s balance_after=%s",
        entry.id,
        membership.id,
        delta,
        reason,
        new_amount,
    )
    return entry


@transaction.atomic
def reverse_entry(entry: LedgerEntry, *, actor=None) -> LedgerEntry:
    """
    التصحيح الوحيد المسموح: قيد عكسي جديد.

    لا UPDATE ولا DELETE على القيد الأصلي — يبقى في السجل مقرونًا
    بعكسه، فيُقرأ التاريخ كاملًا لا منقّحًا.
    """
    if entry.reversed_by.exists():
        raise AlreadyReversed()

    return apply_entry(
        membership=entry.membership,
        program=entry.program,
        delta=-entry.delta,
        reason=LedgerEntry.REASON_REVERSE,
        reverses=entry,
        actor=actor,
    )


@transaction.atomic
def grant_welcome_bonus(*, membership: Membership, program, actor=None) -> LedgerEntry | None:
    """مكافأة الانضمام — مرة واحدة لكل عضوية وبرنامج."""
    bonus = program.rule.welcome_bonus
    if not bonus:
        return None

    already = LedgerEntry.objects.filter(
        membership=membership, program=program, reason=LedgerEntry.REASON_WELCOME
    ).exists()
    if already:
        return None

    return apply_entry(
        membership=membership,
        program=program,
        delta=Decimal(bonus),
        reason=LedgerEntry.REASON_WELCOME,
        actor=actor,
    )


# ═══════════════════════ الاستبدال ═══════════════════════


def _generate_redemption_code() -> str:
    """
    كود من ٨ محارف بلا أحرف ملتبسة.

    حُذفت O و 0 و I و 1 لأن الكود يُقرأ صوتيًا للكاشير في كثير من
    الأحيان، والخلط بينها يعني محاولة فاشلة ووقتًا ضائعًا عند الصندوق.
    """
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(8))


@transaction.atomic
def redeem_reward(*, membership: Membership, reward, actor=None) -> Redemption:
    """يخصم تكلفة المكافأة ويولّد كود صرف صالحًا لمدة محدودة."""
    if not reward.is_active:
        raise LedgerError("هذه المكافأة غير متاحة حاليًا.")

    if not reward.in_stock:
        raise LedgerError("نفدت الكمية من هذه المكافأة.")

    if reward.program.brand_id != membership.brand_id:
        raise LedgerError("هذه المكافأة لا تخص هذه العلامة.")

    entry = apply_entry(
        membership=membership,
        program=reward.program,
        delta=-reward.cost_amount,
        reason=LedgerEntry.REASON_REDEEM,
        actor=actor,
    )

    if reward.stock is not None:
        # الخصم بـ F() لا بقيمة محسوبة — استبدالان متزامنان لآخر قطعة
        # كانا سيمرّان كلاهما لو قرأنا المخزون في بايثون
        type(reward).objects.filter(pk=reward.pk).update(stock=F("stock") - 1)

    # احتمال التصادم على ٨ محارف من ٣٢ ضئيل، لكن الحلقة تجعله مستحيلًا
    for _ in range(5):
        code = _generate_redemption_code()
        if not Redemption.objects.filter(code=code).exists():
            break
    else:  # pragma: no cover - يتطلب خمسة تصادمات متتالية
        raise LedgerError("تعذّر توليد كود فريد. حاول مجددًا.")

    return Redemption.objects.create(
        reward=reward,
        membership=membership,
        ledger_entry=entry,
        code=code,
        expires_at=timezone.now()
        + timezone.timedelta(minutes=settings.REDEMPTION_CODE_TTL_MINUTES),
    )


class RedemptionExpired(LedgerError):
    code = "redemption_expired"
    message = "انتهت صلاحية الكود."
    http_status = status.HTTP_410_GONE


class RedemptionNotFound(LedgerError):
    code = "redemption_not_found"
    message = "كود غير معروف."
    http_status = status.HTTP_404_NOT_FOUND


class RedemptionAlreadyUsed(LedgerError):
    code = "already_used"
    message = "هذا الكود مصروف بالفعل."
    http_status = status.HTTP_409_CONFLICT


class RedemptionWrongBrand(LedgerError):
    code = "wrong_brand"
    message = "هذا الكود لا يخص متجرك."
    http_status = status.HTTP_403_FORBIDDEN


def use_redemption(*, code: str, staff_user) -> Redemption:
    """
    يصرف كود استبدال — مرة واحدة فقط.

    وسم الكود بـ«منتهٍ» يحدث خارج المعاملة عمدًا: الوسم داخلها يتراجع
    مع التراجع الذي يسبّبه رفع الخطأ، فيبقى الكود `pending` إلى الأبد
    ويظهر في تقارير التاجر كالتزام قائم لا وجود له.
    """
    code = code.strip().upper()
    try:
        return _use_redemption_atomic(code=code, staff_user=staff_user)
    except RedemptionExpired:
        Redemption.objects.filter(code=code, status=Redemption.STATUS_PENDING).update(
            status=Redemption.STATUS_EXPIRED, updated_at=timezone.now()
        )
        raise


@transaction.atomic
def _use_redemption_atomic(*, code: str, staff_user) -> Redemption:
    # القفل على صف الاستبدال وحده — راجع التعليق في apps/pos/services.py
    redemption = (
        Redemption.objects.select_for_update(of=("self",))
        .filter(code=code)
        .select_related("reward__program", "membership")
        .first()
    )

    if redemption is None:
        raise RedemptionNotFound()

    if redemption.status == Redemption.STATUS_USED:
        raise RedemptionAlreadyUsed()

    if timezone.now() >= redemption.expires_at:
        raise RedemptionExpired()

    if redemption.membership.brand_id != staff_user.branch.brand_id:
        raise RedemptionWrongBrand()

    redemption.status = Redemption.STATUS_USED
    redemption.used_at = timezone.now()
    redemption.used_by_staff = staff_user
    redemption.save(update_fields=["status", "used_at", "used_by_staff", "updated_at"])
    return redemption


# ═══════════════════════ التحقق من السلامة ═══════════════════════


def verify_balance(membership: Membership, program) -> dict:
    """
    يقارن اللقطة بمجموع القيود.

    أداة تشغيلية تُستدعى في المراجعة الدورية وعند أي شك. اختلاف
    القيمتين يعني وجود مسار يكتب في الرصيد خارج المحرك — وهو عطل
    يستوجب وقف النشر لا إصلاحًا هادئًا.
    """
    ledger_total = LedgerEntry.objects.filter(membership=membership, program=program).aggregate(
        total=Sum("delta")
    )["total"] or Decimal("0")

    snapshot = Balance.objects.filter(membership=membership, program=program).first()
    snapshot_amount = snapshot.amount if snapshot else Decimal("0")

    return {
        "ledger_total": ledger_total,
        "snapshot": snapshot_amount,
        "consistent": ledger_total == snapshot_amount,
        "drift": snapshot_amount - ledger_total,
    }
