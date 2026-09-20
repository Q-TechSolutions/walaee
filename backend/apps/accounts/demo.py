"""
حسابات التجربة.

**المشكلة التي تحلّها:** الدخول يتطلب كودًا يصل برسالة، ولا مزوّد
رسائل متعاقَدًا عليه بعد (القرار ٧). بدون حل، لا أحد يستطيع تجربة
تطبيق العميل — ولا أنت ولا من تعرض عليه المنتج.

**كيف تُحَلّ بأمان:** قائمة أرقام محدّدة بالاسم تقبل كودًا ثابتًا.
أي رقم خارج القائمة يمر بالمسار الكامل بلا أي تغيير: كود عشوائي
مُجزّأ يُرسَل عبر القناة المُعدّة.

**لماذا هذا آمن حتى لو بقي مفعَّلًا في الإنتاج:**
  · الأثر محصور في أرقام مكتوبة صراحةً في متغيّر بيئة. عميل حقيقي
    لن يكون فيها، فلا طريق لانتحال هويته.
  · لا يوجد «وضع تجربة عام» يفتح كل الحسابات — وهو النمط الذي
    يتحوّل إلى ثغرة حين يُنسى مفعَّلًا بعد الإطلاق.
  · القائمة الفارغة (الافتراضي) تعني أن الملف كله بلا أثر.

المُقابل المقبول: من يعرف أرقام التجربة يدخل تلك الحسابات. وهذا
مقصود — هي حسابات عرض لا حسابات عملاء.
"""

import logging

from django.conf import settings

from .validators import normalize_phone

logger = logging.getLogger(__name__)


def demo_phones() -> set[str]:
    """أرقام التجربة مطبَّعة. فارغة = الميزة معطّلة بالكامل."""
    raw = getattr(settings, "DEMO_LOGIN_PHONES", []) or []
    numbers = set()

    for value in raw:
        try:
            numbers.add(normalize_phone(value))
        except Exception:  # noqa: BLE001 - رقم خاطئ في الإعداد لا يُسقط الخدمة
            logger.warning("DEMO_LOGIN_PHONES يحوي رقمًا غير صالح: %s", value)

    return numbers


def is_demo_phone(phone: str) -> bool:
    if not phone:
        return False
    return normalize_phone(phone) in demo_phones()


def demo_code() -> str:
    return str(getattr(settings, "DEMO_LOGIN_CODE", "") or "")


def fixed_code_for(phone: str) -> str | None:
    """
    الكود الثابت لهذا الرقم، أو None إن لم يكن رقم تجربة.

    يُستدعى من `request_otp` قبل توليد الكود العشوائي.
    """
    code = demo_code()
    if not code or not is_demo_phone(phone):
        return None

    logger.info("demo login code issued for %s", phone)
    return code
