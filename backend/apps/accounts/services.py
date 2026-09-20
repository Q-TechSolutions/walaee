"""
منطق أعمال الحسابات.

كل ما هنا قابل للاستدعاء من API ومن Celery ومن أوامر الإدارة بلا تكرار.
"""

import logging
import secrets

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework import status

from apps.common.exceptions import DomainError

from .models import Customer, OtpCode
from .validators import normalize_phone

logger = logging.getLogger(__name__)


class OtpInvalid(DomainError):
    code = "otp_invalid"
    message = "الكود غير صحيح."


class OtpNotFound(DomainError):
    code = "otp_not_found"
    message = "لا يوجد كود فعّال لهذا الرقم. اطلب كودًا جديدًا."
    http_status = status.HTTP_410_GONE


class OtpLocked(DomainError):
    code = "otp_locked"
    message = "تجاوزت عدد المحاولات. اطلب كودًا جديدًا."
    http_status = status.HTTP_429_TOO_MANY_REQUESTS


def _generate_code() -> str:
    length = settings.OTP_LENGTH
    return "".join(secrets.choice("0123456789") for _ in range(length))


@transaction.atomic
def request_otp(
    *, phone: str, purpose: str = OtpCode.PURPOSE_LOGIN, ip: str | None = None
) -> OtpCode:
    """
    يولّد كودًا جديدًا ويبطل ما قبله.

    إبطال الأكواد السابقة مقصود: ترك أكثر من كود فعّال لنفس الرقم
    يوسّع نافذة التخمين بلا فائدة للمستخدم.
    """
    phone = normalize_phone(phone)

    OtpCode.objects.filter(phone=phone, purpose=purpose, consumed_at__isnull=True).update(
        consumed_at=timezone.now()
    )

    code = _generate_code()
    otp = OtpCode.objects.create(
        phone=phone,
        code_hash=make_password(code),
        purpose=purpose,
        expires_at=timezone.now() + timezone.timedelta(seconds=settings.OTP_TTL_SECONDS),
        request_ip=ip,
    )

    transaction.on_commit(lambda: _deliver(phone, code))
    return otp


def _deliver(phone: str, code: str) -> None:
    """
    تسليم الكود عبر القناة المُعدّة.

    مزوّد الرسائل لم يُتعاقَد عليه بعد (القرار ٧ في decisions.md)، فالتسليم
    خلف واجهة واحدة. عند التعاقد يُضاف مزوّد في apps/campaigns/providers/
    ويتغيّر متغيّر بيئة واحد — لا يُلمَس هذا الملف.
    """
    from apps.campaigns.providers import get_sms_provider

    get_sms_provider().send(phone=phone, body=f"كود الدخول إلى ولائي: {code}")


def verify_otp(*, phone: str, code: str, purpose: str = OtpCode.PURPOSE_LOGIN) -> OtpCode:
    """
    يتحقق من الكود ويستهلكه. يرفع خطأ مجال عند أي فشل.

    تسجيل المحاولة الفاشلة يحدث **خارج** المعاملة عمدًا: لو زيد
    العدّاد داخلها ثم رُفع الخطأ، لتراجعت الزيادة مع المعاملة وبقي
    العدّاد صفرًا إلى الأبد — أي أن الحماية من التخمين تصبح معطّلة
    بالكامل بلا أن يظهر ذلك في أي سجل.
    """
    phone = normalize_phone(phone)

    with transaction.atomic():
        otp = (
            OtpCode.objects.select_for_update()
            .filter(phone=phone, purpose=purpose, consumed_at__isnull=True)
            .order_by("-created_at")
            .first()
        )

        if otp is None or otp.is_expired:
            raise OtpNotFound()

        if otp.attempts >= OtpCode.MAX_ATTEMPTS:
            raise OtpLocked()

        if check_password(code, otp.code_hash):
            otp.consumed_at = timezone.now()
            otp.save(update_fields=["consumed_at", "updated_at"])
            return otp

    # الزيادة بـ F() لا بقيمة محسوبة: محاولتان متوازيتان تُحسبان اثنتين
    OtpCode.objects.filter(pk=otp.pk).update(attempts=F("attempts") + 1, updated_at=timezone.now())
    otp.refresh_from_db()
    raise OtpInvalid(remaining=max(0, OtpCode.MAX_ATTEMPTS - otp.attempts))


def login_customer(*, phone: str, code: str, consent_version: str = "") -> tuple[Customer, bool]:
    """
    يتحقق من الكود ويُرجع العميل، منشئًا إياه عند أول دخول.

    التحقق يسبق المعاملة ولا يُلفّ بها: لو كان داخلها، لتراجع تسجيل
    المحاولة الفاشلة مع تراجعها عند رفع الخطأ — وهي نفس الثغرة التي
    يشرحها التعليق في `verify_otp`.

    يُرجع (customer, created).
    """
    verify_otp(phone=phone, code=code)
    return _create_or_resume_customer(phone=phone, consent_version=consent_version)


@transaction.atomic
def _create_or_resume_customer(*, phone: str, consent_version: str) -> tuple[Customer, bool]:
    phone = normalize_phone(phone)

    customer, created = Customer.objects.get_or_create(phone=phone)

    fields = ["last_seen_at", "updated_at"]
    customer.last_seen_at = timezone.now()

    # الموافقة تُسجَّل مرة واحدة بتاريخها ونسخة النص
    if consent_version and not customer.has_consent:
        customer.consent_at = timezone.now()
        customer.consent_version = consent_version
        fields += ["consent_at", "consent_version"]

    # عميل عاد بعد حذف ناعم: يُستأنف حسابه بدل إنشاء هوية جديدة
    if customer.deleted_at is not None:
        customer.deleted_at = None
        fields.append("deleted_at")

    customer.save(update_fields=fields)
    return customer, created


def issue_tokens_for_customer(customer: Customer) -> dict:
    """
    يصدر توكنات JWT لعميل.

    العميل ليس `User`، فالتوكن يُبنى يدويًا ويحمل `scope=customer`
    ليميّزه أي متحقق لاحق عن توكن موظف.
    """
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken()
    refresh["user_id"] = str(customer.id)
    refresh["scope"] = "customer"
    refresh["phone"] = customer.phone

    return {"access": str(refresh.access_token), "refresh": str(refresh)}
