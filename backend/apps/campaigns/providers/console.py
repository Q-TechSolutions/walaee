"""
مزوّد التطوير — يطبع الرسالة في الطرفية بدل إرسالها.

يُبقي مسار تسجيل الدخول كاملًا قابلًا للتشغيل والاختبار بلا عقد
مع أي مزوّد وبلا تكلفة.
"""

import logging
from decimal import Decimal

from .base import SmsMessage, SmsProvider

logger = logging.getLogger(__name__)


class ConsoleSmsProvider(SmsProvider):
    key = "console"

    def send(self, *, phone: str, body: str) -> SmsMessage:
        logger.info("[SMS:console] %s <- %s", phone, body)
        return SmsMessage(phone=phone, body=body, provider_msg_id="console", cost=Decimal("0"))

    def estimate_cost(self, *, count: int) -> Decimal:
        return Decimal("0")
