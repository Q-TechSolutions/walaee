"""سجل بوابات الدفع."""

from django.conf import settings

from .base import PaymentGateway, PaymentIntent
from .manual import ManualTransferGateway

_REGISTRY: dict[str, type[PaymentGateway]] = {
    "manual": ManualTransferGateway,
    "none": ManualTransferGateway,
}

__all__ = ["PaymentGateway", "PaymentIntent", "get_gateway", "register_gateway"]


def register_gateway(key: str, gateway_cls: type[PaymentGateway]) -> None:
    """تُستدعى من بوابة فعلية عند التعاقد عليها."""
    _REGISTRY[key] = gateway_cls


def get_gateway() -> PaymentGateway:
    key = getattr(settings, "PAYMENT_GATEWAY", "manual")
    gateway_cls = _REGISTRY.get(key)

    if gateway_cls is None:
        # بوابة غير مسجّلة لا تُسقِط الفوترة بصمت: التحويل اليدوي
        # يبقي المسار قابلًا للعمل بينما يظهر الخطأ في السجل
        import logging

        logging.getLogger(__name__).error(
            "PAYMENT_GATEWAY=%s غير مسجّلة — يُستخدم التحويل اليدوي بديلًا", key
        )
        gateway_cls = ManualTransferGateway

    return gateway_cls()
