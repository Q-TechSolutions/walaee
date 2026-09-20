"""
سياق الطلب الجاري لسجل التدقيق.

يستخدم ContextVar لا متغيّرًا عامًّا: العامل غير المتزامن ينفّذ عدة
طلبات في نفس الخيط، والمتغيّر العام كان سينسب فعل مستخدم لآخر.
"""

from contextvars import ContextVar

# الافتراضي None لا {}: القيمة القابلة للتغيير تُشارَك بين كل السياقات،
# فتعديلها في طلب يظهر في طلب آخر.
_context: ContextVar[dict | None] = ContextVar("audit_context", default=None)


def set_audit_context(**values) -> None:
    _context.set(values)


def get_audit_context() -> dict:
    return _context.get() or {}


def clear_audit_context() -> None:
    _context.set(None)
