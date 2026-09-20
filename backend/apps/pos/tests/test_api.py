"""
اختبارات طبقة HTTP.

تغطي ما لا تغطيه اختبارات الخدمات: المصادقة، الصلاحيات، شكل الأخطاء،
ورموز الاستجابة المتفق عليها في docs/architecture/api-contract.md
"""

from decimal import Decimal

import pytest
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Customer, OtpCode
from apps.accounts.services import issue_tokens_for_customer
from apps.ledger.models import Transaction
from apps.loyalty.models import Balance
from apps.pos import codes
from tests import factories

pytestmark = pytest.mark.django_db

KNOWN_CODE = "123456"


@pytest.fixture(autouse=True)
def clear_cache():
    """الكاش يخزّن رموز الطرفيات وعدّادات تحديد المعدل معًا."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def customer_api(customer):
    client = APIClient()
    tokens = issue_tokens_for_customer(customer)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


@pytest.fixture
def cashier_api(cashier):
    from rest_framework_simplejwt.tokens import RefreshToken

    client = APIClient()
    refresh = RefreshToken.for_user(cashier.user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


class TestHealth:
    def test_reports_database(self, api):
        response = api.get("/healthz")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "database": "ok"}


class TestOtpEndpoints:
    def test_request_returns_expiry_not_the_code(self, api):
        response = api.post(
            reverse("accounts:otp-request"), {"phone": "01012345678"}, format="json"
        )

        assert response.status_code == 200
        body = response.json()
        assert body["sent"] is True
        assert "expires_in" in body
        # الكود لا يُعاد في الاستجابة أبدًا
        assert "code" not in body

    def test_request_does_not_reveal_registration(self, api):
        """
        تعداد الحسابات ثغرة خصوصية: الرد واحد سواء كان الرقم مسجّلًا أم لا.
        """
        Customer.objects.create(phone="+201012345678")

        known = api.post(reverse("accounts:otp-request"), {"phone": "01012345678"}, format="json")
        cache.clear()
        unknown = api.post(reverse("accounts:otp-request"), {"phone": "01099999999"}, format="json")

        assert known.json() == unknown.json()

    def test_verify_issues_tokens(self, api):
        OtpCode.objects.create(
            phone="+201012345678",
            code_hash=make_password(KNOWN_CODE),
            expires_at=timezone.now() + timezone.timedelta(minutes=5),
        )

        response = api.post(
            reverse("accounts:otp-verify"),
            {"phone": "01012345678", "code": KNOWN_CODE},
            format="json",
        )

        assert response.status_code == 200
        body = response.json()
        assert "access" in body and "refresh" in body
        assert body["is_new"] is True
        assert body["customer"]["phone"] == "+201012345678"

    def test_wrong_code_returns_structured_error(self, api):
        OtpCode.objects.create(
            phone="+201012345678",
            code_hash=make_password(KNOWN_CODE),
            expires_at=timezone.now() + timezone.timedelta(minutes=5),
        )

        response = api.post(
            reverse("accounts:otp-verify"),
            {"phone": "01012345678", "code": "000000"},
            format="json",
        )

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "otp_invalid"

    def test_rate_limited_after_three_requests(self, api):
        """٣ محاولات / ١٥ دقيقة لكل رقم — security.md"""
        for _ in range(3):
            api.post(reverse("accounts:otp-request"), {"phone": "01012345678"}, format="json")

        blocked = api.post(reverse("accounts:otp-request"), {"phone": "01012345678"}, format="json")
        assert blocked.status_code == 429

    def test_rate_limit_is_per_phone(self, api):
        for _ in range(3):
            api.post(reverse("accounts:otp-request"), {"phone": "01012345678"}, format="json")

        other = api.post(reverse("accounts:otp-request"), {"phone": "01088776655"}, format="json")
        assert other.status_code == 200


class TestAuthenticationBoundary:
    def test_anonymous_rejected(self, api):
        response = api.post(reverse("pos:scan-resolve"), {"code": "X"}, format="json")
        assert response.status_code == 401

    def test_customer_token_accepted_on_customer_route(self, customer_api, terminal):
        code = codes.issue_code(terminal.id)

        response = customer_api.post(reverse("pos:scan-resolve"), {"code": code}, format="json")
        assert response.status_code == 200

    def test_customer_token_rejected_on_cashier_route(self, customer_api):
        """توكن عميل لا يفتح شاشة الكاشير."""
        response = customer_api.get(reverse("pos:terminal-code"))
        assert response.status_code == 403

    def test_staff_token_rejected_on_customer_route(self, cashier_api, terminal):
        code = codes.issue_code(terminal.id)

        response = cashier_api.post(reverse("pos:scan-resolve"), {"code": code}, format="json")
        assert response.status_code == 403

    def test_deleted_customer_token_rejected(self, customer, customer_api):
        """توكن صالح زمنيًا لحساب محذوف يُرفض فورًا."""
        customer.anonymize()

        response = customer_api.get(reverse("pos:my-rewards"))
        assert response.status_code == 401


class TestScanResolve:
    def test_returns_brand_and_balances(self, customer_api, terminal, customer, program, brand):
        from apps.ledger.services import apply_entry

        membership = factories.MembershipFactory(customer=customer, brand=brand)
        apply_entry(
            membership=membership,
            program=program,
            delta=Decimal("120"),
            reason="earn",
        )

        code = codes.issue_code(terminal.id)
        response = customer_api.post(reverse("pos:scan-resolve"), {"code": code}, format="json")

        body = response.json()
        assert body["brand"]["name"] == brand.name
        assert body["is_member"] is True
        assert body["balances"][0]["amount"] == "120.00"

    def test_non_member_gets_empty_balances(self, customer_api, terminal):
        code = codes.issue_code(terminal.id)

        body = customer_api.post(reverse("pos:scan-resolve"), {"code": code}, format="json").json()

        assert body["is_member"] is False
        assert body["balances"] == []

    def test_expired_code_returns_410(self, customer_api):
        """رمز منتهٍ = 410 Gone — عقد متفق عليه مع الواجهات."""
        response = customer_api.post(
            reverse("pos:scan-resolve"), {"code": "DEADBEEF"}, format="json"
        )

        assert response.status_code == 410
        assert response.json()["error"]["code"] == "code_expired"


class TestTransactionEndpoints:
    def test_create_then_confirm(self, customer_api, cashier_api, terminal, program):
        code = codes.issue_code(terminal.id)

        created = customer_api.post(
            reverse("pos:create-transaction"),
            {"code": code, "invoice_no": "API-1", "invoice_amount": "300"},
            format="json",
        )
        assert created.status_code == 201
        assert created.json()["status"] == "pending"

        txn_id = created.json()["id"]
        confirmed = cashier_api.post(reverse("pos:confirm", args=[txn_id]))

        assert confirmed.status_code == 200
        assert confirmed.json()["status"] == "confirmed"
        assert Balance.objects.get(program=program).amount == Decimal("300")

    def test_duplicate_invoice_returns_409(self, customer_api, terminal):
        code = codes.issue_code(terminal.id)
        customer_api.post(
            reverse("pos:create-transaction"),
            {"code": code, "invoice_no": "API-DUP", "invoice_amount": "50"},
            format="json",
        )

        code2 = codes.issue_code(terminal.id)
        response = customer_api.post(
            reverse("pos:create-transaction"),
            {"code": code2, "invoice_no": "API-DUP", "invoice_amount": "50"},
            format="json",
        )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "duplicate_invoice"

    def test_missing_code_and_phone_rejected(self, customer_api):
        response = customer_api.post(
            reverse("pos:create-transaction"),
            {"invoice_no": "API-2", "invoice_amount": "50"},
            format="json",
        )

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "validation_error"

    def test_zero_amount_rejected(self, customer_api, terminal):
        code = codes.issue_code(terminal.id)

        response = customer_api.post(
            reverse("pos:create-transaction"),
            {"code": code, "invoice_no": "API-3", "invoice_amount": "0"},
            format="json",
        )
        assert response.status_code == 400


class TestCashierEndpoints:
    def test_terminal_code_returned(self, cashier_api, terminal):
        response = cashier_api.get(reverse("pos:terminal-code"))

        assert response.status_code == 200
        assert len(response.json()["code"]) == 8

    def test_rotate_issues_new_code(self, cashier_api, terminal):
        first = cashier_api.get(reverse("pos:terminal-code")).json()["code"]
        second = cashier_api.post(reverse("pos:terminal-code-rotate")).json()["code"]

        assert first != second
        assert codes.resolve_code(first) is None

    def test_no_terminal_returns_404(self, cashier_api, cashier):
        cashier.branch.terminals.all().delete()

        response = cashier_api.get(reverse("pos:terminal-code"))
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "no_terminal"

    def test_pending_list_scoped_to_branch(self, cashier_api, terminal, customer):
        Transaction.objects.create(
            terminal=terminal,
            customer=customer,
            invoice_no="P-1",
            invoice_amount=Decimal("10"),
        )
        # عملية في فرع آخر يجب ألا تظهر
        other_terminal = factories.TerminalFactory()
        Transaction.objects.create(
            terminal=other_terminal,
            customer=customer,
            invoice_no="P-2",
            invoice_amount=Decimal("10"),
        )

        body = cashier_api.get(reverse("pos:pending")).json()

        assert len(body) == 1
        assert body[0]["invoice_no"] == "P-1"

    def test_manual_path_creates_and_confirms(self, cashier_api, terminal, program):
        response = cashier_api.post(
            reverse("pos:manual"),
            {"phone": "01033445566", "invoice_no": "MAN-1", "invoice_amount": "200"},
            format="json",
        )

        assert response.status_code == 201
        assert response.json()["status"] == "confirmed"
        assert Balance.objects.get(program=program).amount == Decimal("200")


class TestRewardEndpoints:
    def test_lists_rewards_of_joined_brands_only(self, customer_api, customer, brand, program):
        factories.MembershipFactory(customer=customer, brand=brand)
        mine = factories.RewardFactory(program=program, title="قهوة مجانية")

        other_program = factories.LoyaltyProgramFactory()
        factories.ProgramRuleFactory(program=other_program)
        factories.RewardFactory(program=other_program, title="مكافأة علامة أخرى")

        body = customer_api.get(reverse("pos:my-rewards")).json()

        titles = [r["title"] for r in body]
        assert titles == [mine.title]

    def test_redeem_returns_code(self, customer_api, customer, brand, program):
        from apps.ledger.services import apply_entry

        membership = factories.MembershipFactory(customer=customer, brand=brand)
        apply_entry(membership=membership, program=program, delta=Decimal("500"), reason="earn")
        reward = factories.RewardFactory(program=program, cost_amount=Decimal("100"))

        response = customer_api.post(
            reverse("pos:redeem"), {"reward_id": str(reward.id)}, format="json"
        )

        assert response.status_code == 201
        assert len(response.json()["code"]) == 8
        assert Balance.objects.get(program=program).amount == Decimal("400")

    def test_redeem_without_balance_returns_422(self, customer_api, customer, brand, program):
        factories.MembershipFactory(customer=customer, brand=brand)
        reward = factories.RewardFactory(program=program, cost_amount=Decimal("100"))

        response = customer_api.post(
            reverse("pos:redeem"), {"reward_id": str(reward.id)}, format="json"
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "insufficient_balance"

    def test_cashier_uses_redemption_code(
        self, customer_api, cashier_api, customer, brand, branch, program
    ):
        from apps.ledger.services import apply_entry

        membership = factories.MembershipFactory(customer=customer, brand=brand)
        apply_entry(membership=membership, program=program, delta=Decimal("500"), reason="earn")
        reward = factories.RewardFactory(program=program, cost_amount=Decimal("100"))

        code = customer_api.post(
            reverse("pos:redeem"), {"reward_id": str(reward.id)}, format="json"
        ).json()["code"]

        response = cashier_api.post(reverse("pos:use-redemption", args=[code]))

        assert response.status_code == 200
        assert response.json()["status"] == "used"


class TestSchema:
    def test_openapi_schema_generates(self, cashier_api):
        """
        فشل توليد المخطط يعني كسر توثيق العملاء المرتبطين — يُكتشف هنا
        لا في الإنتاج.
        """
        response = cashier_api.get("/api/v1/schema/")
        assert response.status_code == 200


class TestRedemptionErrorContract:
    """
    رموز الاستجابة متفق عليها في docs/architecture/api-contract.md —
    الواجهات تتفرّع عليها، فتغييرها يكسر عملاء مرتبطين.
    """

    @pytest.fixture
    def used_code(self, customer_api, cashier_api, customer, brand, program):
        from apps.ledger.services import apply_entry

        membership = factories.MembershipFactory(customer=customer, brand=brand)
        apply_entry(membership=membership, program=program, delta=Decimal("500"), reason="earn")
        reward = factories.RewardFactory(program=program, cost_amount=Decimal("100"))

        code = customer_api.post(
            reverse("pos:redeem"), {"reward_id": str(reward.id)}, format="json"
        ).json()["code"]
        cashier_api.post(reverse("pos:use-redemption", args=[code]))
        return code

    def test_double_use_returns_409(self, cashier_api, used_code):
        response = cashier_api.post(reverse("pos:use-redemption", args=[used_code]))

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "already_used"

    def test_unknown_code_returns_404(self, cashier_api):
        response = cashier_api.post(reverse("pos:use-redemption", args=["ZZZZZZZZ"]))

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "redemption_not_found"

    def test_wrong_brand_returns_403(self, customer_api, customer, brand, program):
        from rest_framework_simplejwt.tokens import RefreshToken

        from apps.ledger.services import apply_entry

        membership = factories.MembershipFactory(customer=customer, brand=brand)
        apply_entry(membership=membership, program=program, delta=Decimal("500"), reason="earn")
        reward = factories.RewardFactory(program=program, cost_amount=Decimal("100"))
        code = customer_api.post(
            reverse("pos:redeem"), {"reward_id": str(reward.id)}, format="json"
        ).json()["code"]

        foreign_cashier = factories.StaffUserFactory()
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(foreign_cashier.user).access_token}"
        )

        response = client.post(reverse("pos:use-redemption", args=[code]))

        assert response.status_code == 403
        assert response.json()["error"]["code"] == "wrong_brand"
