"""
أخطاء المجال ومعالج الاستجابة الموحّد.

كل خطأ أعمال يحمل `code` ثابتًا لا يتغيّر بتغيّر نص الرسالة، لأن
الواجهات تتفرّع على الرمز لا على النص العربي.
المرجع: docs/architecture/api-contract.md — رموز الاستجابة المتفق عليها
"""

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


class DomainError(Exception):
    """أساس كل أخطاء الأعمال. يُترجَم إلى استجابة HTTP منظّمة."""

    code = "domain_error"
    message = "تعذّر إتمام العملية."
    http_status = status.HTTP_400_BAD_REQUEST

    def __init__(self, message: str | None = None, *, code: str | None = None, **details):
        # `code` يُمرَّر صراحةً حين يشترك خطأان في نفس الصنف ويختلفان
        # في السبب — الواجهة تتفرّع على الرمز لا على النص.
        self.message = message or self.message
        self.code = code or self.code
        self.details = details
        super().__init__(self.message)

    def to_payload(self) -> dict:
        payload = {"error": {"code": self.code, "message": self.message}}
        if self.details:
            payload["error"]["details"] = self.details
        return payload


class CodeExpired(DomainError):
    """رمز نقطة البيع غير موجود أو انتهت صلاحيته."""

    code = "code_expired"
    message = "انتهت صلاحية الرمز. اطلب من الكاشير رمزًا جديدًا."
    http_status = status.HTTP_410_GONE


class DuplicateInvoice(DomainError):
    code = "duplicate_invoice"
    message = "هذه الفاتورة مسجّلة بالفعل على هذه الطرفية."
    http_status = status.HTTP_409_CONFLICT


class InvalidState(DomainError):
    code = "invalid_state"
    message = "حالة العملية لا تسمح بهذا الإجراء."
    http_status = status.HTTP_409_CONFLICT


def walaee_exception_handler(exc, context):
    """يحوّل DomainError إلى استجابة منظّمة، ويترك الباقي لـ DRF."""
    if isinstance(exc, DomainError):
        logger.info(
            "domain_error code=%s path=%s",
            exc.code,
            getattr(context.get("request"), "path", "?"),
        )
        return Response(exc.to_payload(), status=exc.http_status)

    response = drf_exception_handler(exc, context)
    if response is not None and isinstance(response.data, dict):
        # توحيد شكل أخطاء DRF مع شكل أخطاء المجال
        if "error" not in response.data:
            response.data = {
                "error": {
                    "code": "validation_error",
                    "message": "البيانات المُرسَلة غير صالحة.",
                    "details": response.data,
                }
            }
    return response
