"""
حساب ما يُمنح لكل نموذج ولاء.

دالة خالصة بلا لمس قاعدة بيانات: تأخذ القاعدة وقيمة الفاتورة وتُرجع
المقدار. هذا يجعلها قابلة للاختبار بلا تهيئة، ويمنع تسرّب منطق المنح
إلى داخل محرك القيود الذي يجب أن يبقى محايدًا تجاه نوع البرنامج.
"""

from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

from django.conf import settings
from django.utils import timezone

from .models import LoyaltyProgram, ProgramRule

_TWO_PLACES = Decimal("0.01")
_WHOLE = Decimal("1")


def compute_delta(rule: ProgramRule, invoice_amount: Decimal) -> Decimal:
    """
    المقدار الممنوح لفاتورة واحدة. صفر يعني «لا تُكتب قيدًا».

    الفاتورة دون الحد الأدنى لا تمنح شيئًا — هذا ما يمنع تفتيت
    الفواتير الصغيرة للحصول على أختام مجانية.
    """
    amount = Decimal(invoice_amount or 0)
    if amount <= 0 or amount < rule.min_invoice:
        return Decimal("0")

    program_type = rule.program.type

    if program_type in (LoyaltyProgram.TYPE_POINTS, LoyaltyProgram.TYPE_REWARDS):
        # نقاط لكل جنيه — تُقرَّب للأسفل فلا يربح العميل كسرًا لم يدفع مقابله
        return (amount * rule.earn_rate).quantize(_WHOLE, rounding=ROUND_DOWN)

    if program_type in (LoyaltyProgram.TYPE_STAMPS, LoyaltyProgram.TYPE_VISITS):
        # ختم أو زيارة لكل فاتورة مؤهّلة بغضّ النظر عن قيمتها
        return rule.earn_rate.quantize(_WHOLE, rounding=ROUND_DOWN)

    if program_type == LoyaltyProgram.TYPE_CASHBACK:
        # نسبة مئوية تُردّ كقيمة نقدية — تُقرَّب لأقرب قرش
        return (amount * rule.earn_rate / Decimal("100")).quantize(
            _TWO_PLACES, rounding=ROUND_HALF_UP
        )

    if program_type == LoyaltyProgram.TYPE_GIFTS:
        # الهدايا تُمنح يدويًا بقرار من التاجر لا تلقائيًا بالفاتورة
        return Decimal("0")

    return Decimal("0")


def compute_expiry(rule: ProgramRule):
    """
    تاريخ انتهاء الرصيد بعد هذه الحركة.

    كل حركة تُجدّد المدة من تاريخها — عميل يتعامل بانتظام لا يفقد
    رصيده أبدًا، وهو بالضبط السلوك الذي نريد تشجيعه.
    """
    months = rule.expiry_months
    if months is None:
        months = settings.DEFAULT_EXPIRY_MONTHS
    if not months:
        return None

    now = timezone.now()
    year = now.year + (now.month + months - 1) // 12
    month = (now.month + months - 1) % 12 + 1
    day = min(now.day, _days_in_month(year, month))
    return now.replace(year=year, month=month, day=day)


def _days_in_month(year: int, month: int) -> int:
    import calendar

    return calendar.monthrange(year, month)[1]
