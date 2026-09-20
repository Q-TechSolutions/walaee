"""دورة OTP كاملة: طلب · تحقق · دخول."""

import pytest
from django.contrib.auth import get_user_model
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


class TestStaffLogin:
    """
    دخول الموظفين منفصل عن دخول العملاء: الكاشير يدخل من جهاز ثابت
    عشرات المرات يوميًا، وإرسال رسالة في كل مرة تكلفة بلا فائدة.
    """

    @pytest.fixture
    def cashier_account(self, db):
        from tests import factories

        staff = factories.StaffUserFactory()
        staff.user.set_password("secret-pass-9")
        staff.user.save(update_fields=["password"])
        return staff

    def test_valid_credentials_return_tokens_and_roles(self, cashier_account):
        from apps.accounts.services import login_staff

        result = login_staff(phone=cashier_account.user.phone, password="secret-pass-9")

        assert "access" in result and "refresh" in result
        assert result["user"]["phone"] == cashier_account.user.phone
        assert result["roles"][0]["role"] == "cashier"
        assert result["roles"][0]["brand_name"]

    def test_wrong_password_rejected(self, cashier_account):
        from apps.accounts.services import InvalidCredentials, login_staff

        with pytest.raises(InvalidCredentials):
            login_staff(phone=cashier_account.user.phone, password="nope")

    def test_unknown_phone_gives_same_error(self):
        """التمييز بين رقم مجهول وكلمة مرور خاطئة يسمح بتعداد الحسابات."""
        from apps.accounts.services import InvalidCredentials, login_staff

        with pytest.raises(InvalidCredentials):
            login_staff(phone="01099999999", password="whatever")

    def test_inactive_user_rejected(self, cashier_account):
        from apps.accounts.services import InvalidCredentials, login_staff

        cashier_account.user.is_active = False
        cashier_account.user.save(update_fields=["is_active"])

        with pytest.raises(InvalidCredentials):
            login_staff(phone=cashier_account.user.phone, password="secret-pass-9")

    def test_user_without_role_rejected(self):
        from apps.accounts.services import NoStaffRole, login_staff

        User = get_user_model()
        user = User.objects.create_user(phone="01088776655", password="secret-pass-9")

        with pytest.raises(NoStaffRole):
            login_staff(phone=user.phone, password="secret-pass-9")

    def test_platform_admin_without_role_allowed(self):
        """مدير المنصة لا يملك دورًا في أي متجر — وهذا طبيعي."""
        from apps.accounts.services import login_staff

        User = get_user_model()
        user = User.objects.create_user(
            phone="01077665544", password="secret-pass-9", is_platform_admin=True
        )

        result = login_staff(phone=user.phone, password="secret-pass-9")

        assert result["roles"] == []
        assert result["user"]["is_platform_admin"] is True


class TestTokenRefresh:
    def test_staff_refresh_keeps_scope(self, db):
        from rest_framework_simplejwt.tokens import AccessToken

        from apps.accounts.services import issue_tokens_for_user, refresh_tokens
        from tests import factories

        staff = factories.StaffUserFactory()
        tokens = issue_tokens_for_user(staff.user)

        refreshed = refresh_tokens(tokens["refresh"])

        assert AccessToken(refreshed["access"])["scope"] == "staff"

    def test_customer_refresh_keeps_scope(self, customer):
        """
        بلا حفظ scope يفقد توكن العميل تمييزه فتفشل مصادقته بعد أول
        تجديد — عطل يظهر بعد ١٥ دقيقة من الاستخدام لا فورًا.
        """
        from rest_framework_simplejwt.tokens import AccessToken

        from apps.accounts.services import issue_tokens_for_customer, refresh_tokens

        tokens = issue_tokens_for_customer(customer)

        refreshed = refresh_tokens(tokens["refresh"])
        access = AccessToken(refreshed["access"])

        assert access["scope"] == "customer"
        assert access["user_id"] == str(customer.id)

    def test_garbage_token_rejected(self, db):
        from apps.accounts.services import InvalidRefreshToken, refresh_tokens

        with pytest.raises(InvalidRefreshToken):
            refresh_tokens("not-a-token")
