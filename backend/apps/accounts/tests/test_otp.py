"""دورة OTP كاملة: طلب · تحقق · دخول."""

import pytest
from django.contrib.auth.hashers import make_password
from django.utils import timezone

from apps.accounts.models import Customer, OtpCode
from apps.accounts.services import (
    OtpInvalid,
    OtpLocked,
    OtpNotFound,
    login_customer,
    request_otp,
    verify_otp,
)

pytestmark = pytest.mark.django_db

KNOWN_CODE = "123456"


@pytest.fixture
def otp(db):
    """كود معروف مسبقًا — الكود الحقيقي مُجزّأ ولا يُقرأ من الجدول."""
    return OtpCode.objects.create(
        phone="+201012345678",
        code_hash=make_password(KNOWN_CODE),
        expires_at=timezone.now() + timezone.timedelta(minutes=5),
    )


class TestRequestOtp:
    def test_creates_usable_code(self):
        otp = request_otp(phone="01012345678")

        assert otp.phone == "+201012345678"
        assert otp.is_usable
        assert otp.consumed_at is None

    def test_previous_codes_invalidated(self):
        """
        كود واحد فعّال لكل رقم. ترك أكثر من كود صالح يوسّع نافذة
        التخمين بلا فائدة للمستخدم.
        """
        first = request_otp(phone="01012345678")
        request_otp(phone="01012345678")

        first.refresh_from_db()
        assert first.consumed_at is not None

    def test_hash_is_not_the_code(self):
        otp = request_otp(phone="01012345678")
        assert len(otp.code_hash) > 20
        assert otp.code_hash.isdigit() is False


class TestVerifyOtp:
    def test_correct_code_consumes(self, otp):
        result = verify_otp(phone="+201012345678", code=KNOWN_CODE)

        assert result.consumed_at is not None

    def test_wrong_code_counts_attempt(self, otp):
        with pytest.raises(OtpInvalid):
            verify_otp(phone="+201012345678", code="000000")

        otp.refresh_from_db()
        assert otp.attempts == 1
        assert otp.consumed_at is None

    def test_locked_after_max_attempts(self, otp):
        for _ in range(OtpCode.MAX_ATTEMPTS):
            with pytest.raises(OtpInvalid):
                verify_otp(phone="+201012345678", code="000000")

        with pytest.raises(OtpLocked):
            verify_otp(phone="+201012345678", code=KNOWN_CODE)

    def test_expired_code_rejected(self, otp):
        otp.expires_at = timezone.now() - timezone.timedelta(seconds=1)
        otp.save(update_fields=["expires_at"])

        with pytest.raises(OtpNotFound):
            verify_otp(phone="+201012345678", code=KNOWN_CODE)

    def test_no_code_at_all(self):
        with pytest.raises(OtpNotFound):
            verify_otp(phone="+201099999999", code="123456")

    def test_reused_code_rejected(self, otp):
        verify_otp(phone="+201012345678", code=KNOWN_CODE)

        with pytest.raises(OtpNotFound):
            verify_otp(phone="+201012345678", code=KNOWN_CODE)


class TestLoginCustomer:
    def test_creates_customer_on_first_login(self, otp):
        customer, created = login_customer(phone="01012345678", code=KNOWN_CODE)

        assert created is True
        assert customer.phone == "+201012345678"
        assert customer.last_seen_at is not None

    def test_returns_existing_customer(self, otp):
        existing = Customer.objects.create(phone="+201012345678", full_name="سارة")

        customer, created = login_customer(phone="01012345678", code=KNOWN_CODE)

        assert created is False
        assert customer.id == existing.id
        assert customer.full_name == "سارة"

    def test_consent_recorded_once(self, otp):
        customer, _ = login_customer(phone="01012345678", code=KNOWN_CODE, consent_version="v1")
        first_consent = customer.consent_at

        assert customer.has_consent
        assert customer.consent_version == "v1"

        # دخول لاحق لا يعيد كتابة تاريخ الموافقة الأصلي
        OtpCode.objects.create(
            phone="+201012345678",
            code_hash=make_password(KNOWN_CODE),
            expires_at=timezone.now() + timezone.timedelta(minutes=5),
        )
        customer, _ = login_customer(phone="01012345678", code=KNOWN_CODE, consent_version="v2")

        assert customer.consent_at == first_consent
        assert customer.consent_version == "v1"

    def test_soft_deleted_customer_reactivated(self, otp):
        """عميل حذف حسابه ثم عاد: يُستأنف حسابه بدل إنشاء هوية جديدة."""
        Customer.objects.create(phone="+201012345678", deleted_at=timezone.now())

        customer, created = login_customer(phone="01012345678", code=KNOWN_CODE)

        assert created is False
        assert customer.deleted_at is None

    def test_tokens_carry_customer_scope(self, otp):
        from apps.accounts.services import issue_tokens_for_customer

        customer, _ = login_customer(phone="01012345678", code=KNOWN_CODE)
        tokens = issue_tokens_for_customer(customer)

        assert "access" in tokens
        assert "refresh" in tokens


class TestAnonymize:
    def test_identity_cleared_and_id_kept(self):
        """
        حق الحذف مقابل قاعدة «القيود لا تُحذف»: تُمحى الهوية ويبقى
        المعرّف فيظل رصيد التاجر متوازنًا.
        """
        customer = Customer.objects.create(
            phone="+201012345678", full_name="محمد", consent_version="v1"
        )
        original_id = customer.id

        customer.anonymize()

        assert customer.id == original_id
        assert customer.full_name == ""
        assert customer.consent_at is None
        assert customer.phone.startswith("deleted-")
        assert customer.is_deleted
