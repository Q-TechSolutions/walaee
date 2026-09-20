"""
مزوّدو القنوات خلف واجهة واحدة.

القرار ٧ في docs/planning/decisions.md (مزوّد الرسائل المحلي) لم
يُحسم بعد. البناء لا يتوقف عليه: كل استدعاء يمر عبر `ChannelProvider`،
وإضافة مزوّد فعلي لاحقًا = ملف جديد هنا وتغيير متغيّر بيئة واحد —
بلا لمس أي منطق أعمال.
"""

import logging

from django.conf import settings

from .base import ChannelProvider, SentMessage, SmsMessage, SmsProvider
from .console import ConsolePushProvider, ConsoleSmsProvider, ConsoleWhatsAppProvider

logger = logging.getLogger(__name__)

# مزوّدو الرسائل النصية — يختار منهم SMS_PROVIDER
_SMS_REGISTRY: dict[str, type[SmsProvider]] = {
    "console": ConsoleSmsProvider,
}

# مزوّد لكل قناة
_CHANNEL_REGISTRY: dict[str, type[ChannelProvider]] = {
    "push": ConsolePushProvider,
    "whatsapp": ConsoleWhatsAppProvider,
}

__all__ = [
    "ChannelProvider",
    "SentMessage",
    "SmsMessage",
    "SmsProvider",
    "get_channel_provider",
    "get_sms_provider",
    "register_channel_provider",
    "register_provider",
]


def register_provider(key: str, provider_cls: type[SmsProvider]) -> None:
    """تُستدعى من مزوّد رسائل نصية فعلي عند التعاقد عليه."""
    _SMS_REGISTRY[key] = provider_cls


def register_channel_provider(channel: str, provider_cls: type[ChannelProvider]) -> None:
    """تُستدعى من مزوّد قناة فعلي (واتساب أو Web Push)."""
    _CHANNEL_REGISTRY[channel] = provider_cls


def get_sms_provider() -> SmsProvider:
    key = getattr(settings, "SMS_PROVIDER", "console")
    provider_cls = _SMS_REGISTRY.get(key)

    if provider_cls is None:
        # مزوّد غير مسجّل لا يجوز أن يُسقط تسجيل دخول العميل بصمت
        logger.error("SMS_PROVIDER=%s غير مسجّل — يُستخدم console بديلًا", key)
        provider_cls = ConsoleSmsProvider

    return provider_cls()


def get_channel_provider(channel: str) -> ChannelProvider:
    """المزوّد المسؤول عن قناة بعينها."""
    if channel == "sms":
        return get_sms_provider()

    provider_cls = _CHANNEL_REGISTRY.get(channel)
    if provider_cls is None:
        raise ValueError(f"لا يوجد مزوّد مسجّل للقناة: {channel}")

    return provider_cls()
