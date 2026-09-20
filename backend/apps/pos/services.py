"""
منطق نقطة البيع: من الرمز إلى القيد.

`confirm_transaction` هي الخطوة الذرّية: إما أن ينجح كل شيء أو لا
يحدث شيء. لا حالة وسطى — عملية مؤكّدة بلا قيد أو قيد بلا عملية
كلاهما يفسد رصيدًا لا يمكن إصلاحه إلا يدويًا.
"""

import logging
from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import Customer
from apps.common.exceptions import CodeExpired, DuplicateInvoice, InvalidState
from apps.fraud import services as fraud
from apps.ledger.models import LedgerEntry, Transaction
from apps.ledger.services import apply_entry, grant_welcome_bonus
from apps.loyalty.models import LoyaltyProgram, Membership
from apps.loyalty.rules import compute_delta
from apps.tenancy.models import Terminal

from . import codes

logger = logging.getLogger(__name__)


def resolve_terminal(code: str) -> Terminal:
    """يترجم رمز QR إلى طرفية. يرفع CodeExpired عند الفشل."""
    terminal_id = codes.resolve_code(code)
    if not terminal_id:
        raise CodeExpired()

    terminal = (
        Terminal.objects.select_related("branch__brand")
        .filter(pk=terminal_id, is_active=True)
        .first()
    )
    if terminal is None:
        raise CodeExpired()

    return terminal


def active_programs(brand):
    """
    برامج العلامة الفعّالة الآن.

    البرنامج بلا قاعدة لا يُمنح منه شيء — `select_related` يجعل
    غيابها خطأ واضحًا بدل استعلام صامت لكل برنامج.
    """
    now = timezone.now()
    within_window = (Q(starts_at__isnull=True) | Q(starts_at__lte=now)) & (
        Q(ends_at__isnull=True) | Q(ends_at__gte=now)
    )
    return (
        LoyaltyProgram.objects.filter(brand=brand, is_active=True)
        .filter(within_window)
        .select_related("rule", "brand")
    )


@transaction.atomic
def create_transaction(
    *, code: str, customer: Customer, invoice_amount: Decimal, invoice_no: str
) -> Transaction:
    """
    ينشئ عملية معلّقة. لا تُمنح أي نقطة هنا.

    الفصل بين الإنشاء والتأكيد مقصود: العميل يدخل قيمة الفاتورة،
    والتاجر هو من يؤكّد أنها صحيحة. بلا هذا الفصل يكتب العميل ما يشاء.
    """
    terminal = resolve_terminal(code)

    try:
        txn = Transaction.objects.create(
            terminal=terminal,
            customer=customer,
            invoice_no=invoice_no.strip(),
            invoice_amount=Decimal(invoice_amount),
            code_used=code.strip().upper(),
            status=Transaction.STATUS_PENDING,
        )
    except IntegrityError as exc:
        raise DuplicateInvoice() from exc

    # الرمز يُستهلك فورًا — لا ينتظر التأكيد
    codes.consume_code(code)

    logger.info("txn created id=%s terminal=%s", txn.id, terminal.id)
    return txn


@transaction.atomic
def confirm_transaction(txn_id, *, staff_user) -> list[LedgerEntry]:
    """
    التأكيد الذرّي — قلب النظام.

    كل ما بداخل هذه الدالة ينجح معًا أو يفشل معًا:
      قفل العملية ← فحص الحالة ← فحص الصلاحية ← العضوية ←
      تطبيق القواعد ← كتابة القيود ← تحديث الحالة ← قواعد الاحتيال.

    القفل على `Transaction` هو ما يمنع التأكيد المزدوج: ضغطتان
    متزامنتان تتسلسلان، والثانية تجد الحالة `confirmed` فتُرفَض.
    """
    # of=("self",) يقصر القفل على صف العملية وحده. بدونه يحاول
    # PostgreSQL قفل الجداول المضمومة أيضًا، و `customer` قابل لـ null
    # فيصير الضم LEFT OUTER — وقفل الطرف القابل للفراغ مرفوض.
    txn = (
        Transaction.objects.select_for_update(of=("self",))
        .select_related("terminal__branch__brand", "customer")
        .get(pk=txn_id)
    )

    if txn.status != Transaction.STATUS_PENDING:
        raise InvalidState("هذه العملية مؤكّدة أو ملغاة بالفعل.", code="not_pending")

    # كاشير من فرع آخر لا يؤكّد عمليات ليست له
    if staff_user.branch_id != txn.terminal.branch_id:
        raise PermissionDenied("لا تملك صلاحية تأكيد عمليات هذا الفرع.")

    if txn.customer_id is None:
        raise InvalidState("لا يوجد عميل مرتبط بهذه العملية.", code="no_customer")

    brand = txn.terminal.branch.brand
    membership, joined = Membership.objects.get_or_create(customer=txn.customer, brand=brand)

    entries: list[LedgerEntry] = []

    for program in active_programs(brand):
        rule = getattr(program, "rule", None)
        if rule is None:
            logger.warning("program without rule id=%s — skipped", program.id)
            continue

        # عميل جديد: مكافأة الانضمام قبل أول منح
        if joined:
            bonus = grant_welcome_bonus(membership=membership, program=program, actor=staff_user)
            if bonus:
                entries.append(bonus)

        delta = compute_delta(rule, txn.invoice_amount)
        if delta <= 0:
            continue

        entries.append(
            apply_entry(
                membership=membership,
                program=program,
                delta=delta,
                reason=LedgerEntry.REASON_EARN,
                transaction_obj=txn,
                actor=staff_user,
            )
        )

    txn.status = Transaction.STATUS_CONFIRMED
    txn.staff_user = staff_user
    txn.confirmed_at = timezone.now()
    txn.save(update_fields=["status", "staff_user", "confirmed_at", "updated_at"])

    # قواعد الاحتيال داخل نفس المعاملة — لا تُؤجَّل
    fraud.evaluate(txn)

    # المهام غير المتزامنة بعد نجاح COMMIT فقط: إشعار العميل بنقاط
    # لم تُكتب بعد وعد كاذب إن فشلت المعاملة
    transaction.on_commit(lambda: _notify_after_confirm(txn.id))

    logger.info("txn confirmed id=%s entries=%s", txn.id, len(entries))
    return entries


def _notify_after_confirm(txn_id) -> None:
    from .tasks import notify_customer

    notify_customer.delay(str(txn_id))


@transaction.atomic
def create_manual_transaction(
    *, staff_user, phone: str, invoice_amount: Decimal, invoice_no: str
) -> Transaction:
    """
    المسار اليدوي: التاجر يُدخل رقم الهاتف بدل مسح العميل.

    ضروري لأن نسبة من العملاء لن تحمل التطبيق أبدًا، ورفضهم يعني
    خسارة التاجر لجزء من قاعدته — وهو أول سبب لإلغاء الاشتراك.
    """
    terminal = (
        Terminal.objects.select_related("branch__brand")
        .filter(branch=staff_user.branch, is_active=True)
        .first()
    )
    if terminal is None:
        raise InvalidState("لا توجد نقطة بيع نشطة في هذا الفرع.", code="no_terminal")

    from apps.accounts.validators import normalize_phone

    customer, _ = Customer.objects.get_or_create(phone=normalize_phone(phone))

    try:
        txn = Transaction.objects.create(
            terminal=terminal,
            customer=customer,
            staff_user=staff_user,
            invoice_no=invoice_no.strip(),
            invoice_amount=Decimal(invoice_amount),
            status=Transaction.STATUS_PENDING,
        )
    except IntegrityError as exc:
        raise DuplicateInvoice() from exc

    return txn
