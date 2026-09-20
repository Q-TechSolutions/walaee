"""
مزوّدو التطوير — يطبعون الرسالة في الطرفية بدل إرسالها.

يُبقون كل مسارات الرسائل قابلة للتشغيل والاختبار بلا عقد مع أي
مزوّد وبلا تكلفة. القرار ٧ في docs/planning/decisions.md لم يُحسم،
وعند حسمه يُضاف ملف مزوّد هنا ويتغيّر متغيّر بيئة واحد.
"""

import logging
from decimal import Decimal

from .base import ChannelProvider, SentMessage, SmsProvider

logger = logging.getLogger(__name__)


class ConsoleSmsProvider(SmsProvider):
    key = "console"
    channel = "sms"

    def send(self, *, phone: str, body: str) -> SentMessage:
        logger.info("[SMS:console] %s <- %s", phone, body)
        return SentMessage(phone=phone, body=body, provider_msg_id="console-sms", cost=Decimal("0"))

    def estimate_cost(self, *, count: int) -> Decimal:
        return Decimal("0")


class ConsolePushProvider(ChannelProvider):
    key = "console-push"
    channel = "push"

    def send(self, *, phone: str, body: str) -> SentMessage:
        logger.info("[PUSH:console] %s <- %s", phone, body)
        return SentMessage(
            phone=phone, body=body, provider_msg_id="console-push", cost=Decimal("0")
        )


class ConsoleWhatsAppProvider(ChannelProvider):
    key = "console-whatsapp"
    channel = "whatsapp"

    def send(self, *, phone: str, body: str) -> SentMessage:
        logger.info("[WA:console] %s <- %s", phone, body)
        return SentMessage(phone=phone, body=body, provider_msg_id="console-wa", cost=Decimal("0"))
