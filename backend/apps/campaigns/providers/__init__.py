"""
مزوّدو القنوات خلف واجهة واحدة.

القرار ٧ في docs/planning/decisions.md (مزوّد الرسائل المحلي) لم يُحسم
بعد، والقرار ٨ (بوابة الدفع) كذلك. البناء لا يتوقف عليهما: كل
استدعاء يمر عبر `SmsProvider`، وإضافة مزوّد فعلي لاحقًا = ملف جديد
هنا وتغيير متغيّر بيئة واحد — بلا لمس أي منطق أعمال.
"""

from django.conf import settings

from .base import SmsMessage, SmsProvider
from .console import ConsoleSmsProvider

_REGISTRY: dict[str, type[SmsProvider]] = {
    "console": ConsoleSmsProvider,
}

__all__ = ["SmsMessage", "SmsProvider", "get_sms_provider", "register_provider"]


def register_provider(key: str, provider_cls: type[SmsProvider]) -> None:
    """تُستدعى من مزوّد فعلي عند التعاقد عليه."""
    _REGISTRY[key] = provider_cls


def get_sms_provider() -> SmsProvider:
    key = getattr(settings, "SMS_PROVIDER", "console")
    provider_cls = _REGISTRY.get(key)

    if provider_cls is None:
        # مزوّد غير مسجّل لا يجوز أن يُسقط تسجيل دخول العميل بصمت
        import logging

        logging.getLogger(__name__).error("SMS_PROVIDER=%s غير مسجّل — يُستخدم console بديلًا", key)
        provider_cls = ConsoleSmsProvider

    return provider_cls()
