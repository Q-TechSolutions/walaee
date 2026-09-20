"""
دخول حسابات التجربة.

الخطر الوحيد في هذه الميزة هو أن تتسرّب إلى رقم حقيقي. معظم
الاختبارات هنا تثبت أنها **لا تفعل**: رقم خارج القائمة يمر بالمسار
الكامل، والقائمة الفارغة تعطّل الميزة بالكامل.
"""

import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts import demo
from apps.accounts.models import Customer, OtpCode
from apps.accounts.services import OtpInvalid, login_customer, request_otp

pytestmark = pytest.mark.django_db

DEMO_PHONE = "01111111111"
DEMO_NORMALIZED = "+201111111111"
REAL_PHONE = "01999888777"
CODE = "123456"

demo_settings = override_settings(DEMO_LOGIN_PHONES=[DEMO_PHONE], DEMO_LOGIN_CODE=CODE)


@pytest.fixture
def api():
    return APIClient()


class TestDemoPhoneDetection:
    @demo_settings
    def test_listed_number_is_demo(self):
        assert demo.is_demo_phone(DEMO_PHONE) is True
        # الصيغة الدولية لنفس الرقم أيضًا
        assert demo.is_demo_phone(DEMO_NORMALIZED) is True

    @demo_settings
    def test_unlisted_number_is_not(self):
        assert demo.is_demo_phone(REAL_PHONE) is False

    @override_settings(DEMO_LOGIN_PHONES=[], DEMO_LOGIN_CODE=CODE)
    def test_empty_list_disables_feature(self):
        assert demo.is_demo_phone(DEMO_PHONE) is False
        assert demo.fixed_code_for(DEMO_PHONE) is None

    @override_settings(DEMO_LOGIN_PHONES=[DEMO_PHONE], DEMO_LOGIN_CODE="")
    def test_empty_code_disables_feature(self):
        assert demo.fixed_code_for(DEMO_PHONE) is None

    @override_settings(DEMO_LOGIN_PHONES=["ليس رقمًا", DEMO_PHONE], DEMO_LOGIN_CODE=CODE)
    def test_invalid_entry_does_not_break_the_rest(self):
        """رقم خاطئ في الإعداد لا يُسقط الخدمة ولا يعطّل الأرقام السليمة."""
        assert demo.is_demo_phone(DEMO_PHONE) is True

    def test_defaults_are_off(self):
        """الافتراضي بلا أرقام وبلا كود — الميزة بلا أثر."""
        assert demo.demo_phones() == set()
        assert demo.fixed_code_for(DEMO_PHONE) is None


class TestDemoLoginWorks:
    @demo_settings
    def test_fixed_code_logs_in(self):
        request_otp(phone=DEMO_PHONE)

        customer, created = login_customer(phone=DEMO_PHONE, code=CODE)

        assert created is True
        assert customer.phone == DEMO_NORMALIZED

    @demo_settings
    def test_code_is_still_hashed_in_db(self):
        """
        الكود ثابت لكنه يُخزَّن مُجزّأً كغيره: لا استثناء في طريقة
        التخزين، فلا مسار ثانٍ يمكن أن ينحرف عن الأول.
        """
        otp = request_otp(phone=DEMO_PHONE)

        assert otp.code_hash != CODE
        assert len(otp.code_hash) > 20

    @demo_settings
    def test_wrong_code_still_rejected(self):
        """رقم التجربة لا يقبل أي كود — يقبل الكود الثابت وحده."""
        request_otp(phone=DEMO_PHONE)

        with pytest.raises(OtpInvalid):
            login_customer(phone=DEMO_PHONE, code="000000")

    @demo_settings
    def test_attempts_still_counted(self):
        """حماية التخمين تعمل على أرقام التجربة أيضًا."""
        otp = request_otp(phone=DEMO_PHONE)

        with pytest.raises(OtpInvalid):
            login_customer(phone=DEMO_PHONE, code="000000")

        otp.refresh_from_db()
        assert otp.attempts == 1


class TestRealNumbersUnaffected:
    @demo_settings
    def test_real_number_gets_random_code(self):
        """
        الضمان الأهم: رقم خارج القائمة لا يقبل الكود الثابت إطلاقًا.
        """
        request_otp(phone=REAL_PHONE)

        with pytest.raises(OtpInvalid):
            login_customer(phone=REAL_PHONE, code=CODE)

    @demo_settings
    def test_real_number_code_is_not_the_demo_code(self):
        from django.contrib.auth.hashers import check_password

        otp = request_otp(phone=REAL_PHONE)

        assert check_password(CODE, otp.code_hash) is False

    @demo_settings
    def test_real_number_response_hides_code(self, api):
        response = api.post(reverse("accounts:otp-request"), {"phone": REAL_PHONE}, format="json")

        body = response.json()
        assert body["sent"] is True
        assert "code" not in body
        assert "demo" not in body

    @demo_settings
    def test_demo_response_shows_code(self, api):
        response = api.post(reverse("accounts:otp-request"), {"phone": DEMO_PHONE}, format="json")

        body = response.json()
        assert body["demo"] is True
        assert body["code"] == CODE

    @override_settings(DEMO_LOGIN_PHONES=[], DEMO_LOGIN_CODE="")
    def test_feature_off_never_reveals_anything(self, api):
        response = api.post(reverse("accounts:otp-request"), {"phone": DEMO_PHONE}, format="json")

        assert "code" not in response.json()


class TestFullDemoFlow:
    @demo_settings
    def test_login_through_api(self, api):
        """الدورة كما يعيشها من يجرّب التطبيق."""
        requested = api.post(
            reverse("accounts:otp-request"), {"phone": DEMO_PHONE}, format="json"
        ).json()

        verified = api.post(
            reverse("accounts:otp-verify"),
            {"phone": DEMO_PHONE, "code": requested["code"]},
            format="json",
        )

        assert verified.status_code == 200
        body = verified.json()
        assert "access" in body
        assert body["customer"]["phone"] == DEMO_NORMALIZED

    @demo_settings
    def test_token_opens_the_wallet(self, api):
        requested = api.post(
            reverse("accounts:otp-request"), {"phone": DEMO_PHONE}, format="json"
        ).json()
        session = api.post(
            reverse("accounts:otp-verify"),
            {"phone": DEMO_PHONE, "code": requested["code"]},
            format="json",
        ).json()

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {session['access']}")

        assert client.get(reverse("me:cards")).status_code == 200

    @demo_settings
    def test_existing_customer_keeps_their_data(self):
        existing = Customer.objects.create(phone=DEMO_NORMALIZED, full_name="سارة عبد الله")
        request_otp(phone=DEMO_PHONE)

        customer, created = login_customer(phone=DEMO_PHONE, code=CODE)

        assert created is False
        assert customer.id == existing.id
        assert customer.full_name == "سارة عبد الله"

    @demo_settings
    def test_code_expires_like_any_other(self):
        """الكود ثابت لكن صلاحيته الزمنية كغيره — لا استثناء."""
        from django.utils import timezone

        from apps.accounts.services import OtpNotFound

        request_otp(phone=DEMO_PHONE)
        OtpCode.objects.filter(phone=DEMO_NORMALIZED).update(
            expires_at=timezone.now() - timezone.timedelta(seconds=1)
        )

        with pytest.raises(OtpNotFound):
            login_customer(phone=DEMO_PHONE, code=CODE)


class TestThrottleExemption:
    """
    أرقام التجربة معفاة من حد OTP. الإعفاء يجب أن يبقى محصورًا
    فيها — وإلا صار بابًا لإغراق أي رقم حقيقي برسائل.
    """

    @demo_settings
    def test_demo_phone_never_throttled(self, api):
        # أضعاف الحد المسموح (٣ / ١٥ دقيقة)
        codes = [
            api.post(
                reverse("accounts:otp-request"), {"phone": DEMO_PHONE}, format="json"
            ).status_code
            for _ in range(8)
        ]

        assert codes == [200] * 8

    @demo_settings
    def test_real_phone_still_throttled(self, api):
        """الضمان: الإعفاء لا يتسرّب إلى رقم خارج القائمة."""
        for _ in range(3):
            api.post(reverse("accounts:otp-request"), {"phone": REAL_PHONE}, format="json")

        blocked = api.post(reverse("accounts:otp-request"), {"phone": REAL_PHONE}, format="json")

        assert blocked.status_code == 429

    @override_settings(DEMO_LOGIN_PHONES=[], DEMO_LOGIN_CODE="")
    def test_feature_off_throttles_everyone(self, api):
        for _ in range(3):
            api.post(reverse("accounts:otp-request"), {"phone": DEMO_PHONE}, format="json")

        blocked = api.post(reverse("accounts:otp-request"), {"phone": DEMO_PHONE}, format="json")

        assert blocked.status_code == 429

    @demo_settings
    def test_throttle_error_says_what_happened(self, api):
        """
        ٤٢٩ كان يُسمّى «validation_error»، فيرى المستخدم «البيانات
        غير صالحة» ويصحّح مدخلاته مرارًا بلا أن يفهم أن عليه
        الانتظار فحسب.
        """
        for _ in range(3):
            api.post(reverse("accounts:otp-request"), {"phone": REAL_PHONE}, format="json")

        blocked = api.post(reverse("accounts:otp-request"), {"phone": REAL_PHONE}, format="json")

        assert blocked.status_code == 429
        assert blocked.json()["error"]["code"] == "rate_limited"
        assert "انتظر" in blocked.json()["error"]["message"]


class TestErrorCodesFollowStatus:
    def test_unauthenticated(self, api):
        response = api.get(reverse("me:cards"))

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthenticated"

    def test_forbidden(self, customer):
        from apps.accounts.services import issue_tokens_for_customer

        client = APIClient()
        tokens = issue_tokens_for_customer(customer)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        response = client.get(reverse("ledger:dashboard"))

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    def test_validation_error_kept_for_bad_input(self, api):
        response = api.post(reverse("accounts:otp-request"), {"phone": ""}, format="json")

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "validation_error"
