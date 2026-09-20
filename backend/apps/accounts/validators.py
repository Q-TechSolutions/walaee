"""
تطبيع أرقام الهواتف والتحقق منها.

التطبيع إلزامي قبل أي بحث أو حفظ: نفس الرقم يُكتب بأشكال كثيرة
(‎+20 و ‎0020 و ‎01 ومسافات وشرطات وأرقام عربية-هندية)، وبدون توحيده
يظهر العميل الواحد كعدة عملاء وينقسم رصيده — وهي خسارة ثقة مباشرة.

القرار ٦ في docs/planning/decisions.md لم يُحسم بعد، فالرمز الدولي
الافتراضي مصر ويُقرأ من الإعدادات لا من ثابت مدفون في الكود.
"""

import re

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

# الأرقام العربية-الهندية ← اللاتينية
_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")

_SEPARATORS = re.compile(r"[\s\-()./]")

DEFAULT_COUNTRY_CODE = "20"
NATIONAL_PREFIX = "0"

# سِمة الحساب بعد إخفاء الهوية. لا تُطبَّع ولا تُقبل كمدخل من مستخدم —
# وجودها في عمود الهاتف ضرورة تقنية: العمود فريد، وتفريغه لكل حساب
# محذوف كان سيجعل الحسابات المحذوفة تتصادم مع بعضها.
ANONYMIZED_PREFIX = "deleted-"

phone_validator = RegexValidator(
    regex=r"^(\+\d{8,19}|deleted-[0-9a-f]{1,32})$",
    message="رقم الهاتف يجب أن يكون بصيغة دولية، مثل ‎+201012345678.",
)


def normalize_phone(raw: str | None) -> str:
    """
    يعيد الرقم بصيغة E.164 المبسطة: ‎+<code><subscriber>.

    الأشكال المقبولة كلها تؤدي لنفس الناتج:
        01012345678   ->  +201012345678
        ٠١٠١٢٣٤٥٦٧٨   ->  +201012345678
        0020 101 234 5678 -> +201012345678
        +201012345678 ->  +201012345678
    """
    if not raw:
        return ""

    # الحساب المُخفى الهوية يُمرَّر كما هو — لا رقم فيه أصلًا ليُطبَّع
    if str(raw).startswith(ANONYMIZED_PREFIX):
        return str(raw)

    value = str(raw).strip().translate(_ARABIC_DIGITS)
    value = _SEPARATORS.sub("", value)

    if value.startswith("00"):
        value = "+" + value[2:]

    if value.startswith("+"):
        digits = value[1:]
    elif value.startswith(NATIONAL_PREFIX):
        # رقم محلي: يُسقَط الصفر ويُضاف رمز الدولة
        digits = DEFAULT_COUNTRY_CODE + value[len(NATIONAL_PREFIX) :]
    elif value.startswith(DEFAULT_COUNTRY_CODE):
        digits = value
    else:
        digits = DEFAULT_COUNTRY_CODE + value

    if not digits.isdigit():
        raise ValidationError("رقم الهاتف يحتوي على محارف غير رقمية.")

    return "+" + digits
