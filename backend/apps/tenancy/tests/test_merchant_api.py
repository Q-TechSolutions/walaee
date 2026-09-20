"""
لوحة التاجر عبر HTTP.

أهم ما تختبره هذه الملفات ليس أن النقاط تعمل، بل أن **الأدوار
محترمة**: الكاشير لا يرى تقريرًا، والمدير لا يرى رقمًا ماليًا،
ولا أحد يرى بيانات علامة أخرى.
"""

from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.billing.models import MessageCredit, Plan
from apps.billing.services import apply_credit, get_subscription
from apps.ledger.services import apply_entry
from apps.tenancy.models import Branch, StaffUser, Terminal
from tests import factories

pytestmark = pytest.mark.django_db


def _client(staff):
    client = APIClient()
    token = RefreshToken.for_user(staff.user).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.fixture
def owner(branch):
    return factories.StaffUserFactory(branch=branch, role=StaffUser.ROLE_OWNER)


@pytest.fixture
def manager(branch):
    return factories.StaffUserFactory(branch=branch, role=StaffUser.ROLE_MANAGER)


@pytest.fixture
def owner_api(owner):
    return _client(owner)


@pytest.fixture
def manager_api(manager):
    return _client(manager)


@pytest.fixture
def cashier_api(cashier):
    return _client(cashier)


@pytest.fixture
def growth_brand(brand):
    subscription = get_subscription(brand.organization)
    subscription.plan = Plan.GROWTH
    subscription.save(update_fields=["plan"])
    return brand


# ═══════════════════════ الأدوار ═══════════════════════


class TestRoleBoundaries:
    def test_cashier_cannot_see_dashboard(self, cashier_api):
        """الكاشير يؤكّد العمليات ولا يرى التقارير — security.md"""
        assert cashier_api.get(reverse("ledger:dashboard")).status_code == 403

    def test_manager_can_see_dashboard(self, manager_api):
        assert manager_api.get(reverse("ledger:dashboard")).status_code == 200

    def test_manager_cannot_see_liability(self, manager_api):
        """الالتزام القائم رقم مالي — للمالك وحده."""
        assert manager_api.get(reverse("ledger:liability")).status_code == 403

    def test_owner_can_see_liability(self, owner_api):
        assert owner_api.get(reverse("ledger:liability")).status_code == 200

    def test_manager_cannot_manage_branches(self, manager_api):
        assert manager_api.get(reverse("tenancy:branches")).status_code == 403

    def test_manager_cannot_edit_program_rule(self, manager_api, program):
        response = manager_api.put(
            reverse("loyalty:program-rule", args=[program.id]),
            {"earn_rate": "5"},
            format="json",
        )
        assert response.status_code == 403

    def test_customer_token_rejected_everywhere(self, customer):
        from apps.accounts.services import issue_tokens_for_customer

        client = APIClient()
        tokens = issue_tokens_for_customer(customer)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        assert client.get(reverse("ledger:dashboard")).status_code == 403


# ═══════════════════════ اللوحة ═══════════════════════


class TestGovernance:
    def test_free_plan_blocks_second_branch(self, owner_api, brand):
        response = owner_api.post(reverse("tenancy:branches"), {"name": "فرع ثانٍ"}, format="json")

        assert response.status_code == 402
        assert response.json()["error"]["code"] == "plan_limit_reached"

    def test_growth_plan_allows_branch(self, owner_api, growth_brand):
        response = owner_api.post(reverse("tenancy:branches"), {"name": "فرع ثانٍ"}, format="json")

        assert response.status_code == 201
        assert Branch.objects.filter(brand=growth_brand).count() == 2

    def test_add_terminal(self, owner_api, growth_brand, branch):
        response = owner_api.post(
            reverse("tenancy:terminals"),
            {"label": "كاشير ٣", "branch_id": str(branch.id)},
            format="json",
        )

        assert response.status_code == 201
        assert Terminal.objects.filter(branch=branch).count() == 1

    def test_add_staff_creates_user(self, owner_api, growth_brand, branch):
        response = owner_api.post(
            reverse("tenancy:staff"),
            {
                "phone": "01055443322",
                "full_name": "موظف جديد",
                "role": "cashier",
                "branch_id": str(branch.id),
            },
            format="json",
        )

        assert response.status_code == 201
        assert response.json()["phone"] == "+201055443322"

    def test_cannot_disable_self(self, owner_api, owner):
        response = owner_api.delete(reverse("tenancy:staff-detail", args=[owner.id]))

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "cannot_disable_self"

    def test_disable_other_staff(self, owner_api, cashier):
        response = owner_api.delete(reverse("tenancy:staff-detail", args=[cashier.id]))

        assert response.status_code == 200
        cashier.refresh_from_db()
        assert cashier.is_active is False

    def test_terminal_list_hides_active_code(self, owner_api, terminal):
        """الرمز الفعّال لا يُعرض في قائمة إدارية — عرضه يعني مسحه من بعيد."""
        body = owner_api.get(reverse("tenancy:terminals")).json()

        assert body
        assert "current_code" not in body[0]


# ═══════════════════════ البرامج والمكافآت ═══════════════════════


class TestPrograms:
    def test_rule_update_is_forward_only(self, owner_api, program, membership):
        apply_entry(membership=membership, program=program, delta=Decimal("100"), reason="earn")

        response = owner_api.put(
            reverse("loyalty:program-rule", args=[program.id]),
            {"earn_rate": "5", "max_per_day": "2000"},
            format="json",
        )

        assert response.status_code == 200
        assert "المنح الجديدة فقط" in response.json()["note"]

        # الرصيد القديم لم يتغيّر
        from apps.loyalty.models import Balance

        assert Balance.objects.get(membership=membership).amount == Decimal("100")

    def test_new_program_gets_a_rule(self, owner_api, growth_brand):
        response = owner_api.post(
            reverse("loyalty:programs"),
            {"name": "أختام", "type": "stamps"},
            format="json",
        )

        assert response.status_code == 201
        assert response.json()["rule"] is not None

    def test_free_plan_blocks_second_program(self, owner_api, program):
        response = owner_api.post(
            reverse("loyalty:programs"),
            {"name": "برنامج ثانٍ", "type": "visits"},
            format="json",
        )

        assert response.status_code == 402

    def test_add_reward(self, manager_api, program):
        response = manager_api.post(
            reverse("loyalty:rewards"),
            {
                "title": "عصير مجاني",
                "cost_amount": "80",
                "merchant_cost": "12",
                "program_id": str(program.id),
            },
            format="json",
        )

        assert response.status_code == 201
        assert response.json()["unit_label"] == "نقطة"


class TestCustomerList:
    def test_search_normalizes_phone(self, manager_api, brand):
        customer = factories.CustomerFactory(phone="01099887766", full_name="هدى")
        factories.MembershipFactory(customer=customer, brand=brand)

        # التاجر يكتب الرقم محليًا والمخزَّن دولي
        body = manager_api.get(reverse("loyalty:customers"), {"search": "01099887766"}).json()

        assert body["count"] == 1
        assert body["results"][0]["full_name"] == "هدى"

    def test_search_by_name(self, manager_api, brand):
        customer = factories.CustomerFactory(full_name="محمود حسن")
        factories.MembershipFactory(customer=customer, brand=brand)

        body = manager_api.get(reverse("loyalty:customers"), {"search": "محمود"}).json()

        assert body["count"] == 1

    def test_other_brand_customers_invisible(self, manager_api, brand):
        factories.MembershipFactory(brand=brand)
        factories.MembershipFactory()  # علامة أخرى

        body = manager_api.get(reverse("loyalty:customers")).json()

        assert body["count"] == 1

    def test_detail_shows_activity_and_spend(self, manager_api, brand, program, customer):
        membership = factories.MembershipFactory(customer=customer, brand=brand)
        apply_entry(membership=membership, program=program, delta=Decimal("75"), reason="earn")

        body = manager_api.get(reverse("loyalty:customer", args=[membership.id])).json()

        assert len(body["recent_activity"]) == 1
        assert body["recent_activity"][0]["delta"] == "75.00"
        assert body["total_spend"] == "0"


# ═══════════════════════ الفوترة ═══════════════════════


class TestBillingEndpoints:
    def test_subscription_shows_limits_and_usage(self, owner_api, brand, branch):
        body = owner_api.get(reverse("billing:subscription")).json()

        assert body["plan"] == "free"
        assert body["limits"]["max_branches"] == "1"
        assert body["usage"]["branches"] == 1
        assert body["message_balance"] == 0

    def test_wallet_history(self, owner_api, brand):
        apply_credit(
            organization=brand.organization,
            delta=250,
            reason=MessageCredit.REASON_TOPUP,
        )

        body = owner_api.get(reverse("billing:wallet")).json()

        assert body["balance"] == 250
        assert body["history"][0]["delta"] == 250

    def test_invoice_payment_instructions(self, owner_api, brand):
        from apps.billing.services import issue_invoice

        subscription = get_subscription(brand.organization)
        invoice = issue_invoice(subscription)

        body = owner_api.get(reverse("billing:payment", args=[invoice.id])).json()

        assert body["reference"] == invoice.number
        assert "تحويل" in body["instructions"] or invoice.number in body["instructions"]
