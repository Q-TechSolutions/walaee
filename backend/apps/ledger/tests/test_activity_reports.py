"""
ما تحتاجه شاشات لوحة التاجر لترسم نفسها كما في العرض المعتمد:
تدفّق العمليات، ووردية الكاشير، وعدّ استبدال كل مكافأة.

الخطر المشترك بين الثلاثة أنها أرقام «تبدو معقولة» مهما كانت
خاطئة: لا أحد يراجع «٤١ عملية اليوم» بعدّها يدويًا. لذلك تُثبَّت
حدودها هنا — ما يُحتسب وما لا يُحتسب، ولمن.
"""

from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.ledger import reports
from apps.ledger.models import Transaction
from apps.pos import codes
from apps.pos import services as pos
from apps.tenancy.models import StaffUser
from tests import factories

pytestmark = pytest.mark.django_db


def client_for(staff) -> APIClient:
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(staff.user).access_token}"
    )
    return client


@pytest.fixture
def manager(branch):
    return factories.StaffUserFactory(branch=branch, role=StaffUser.ROLE_MANAGER)


def earn(membership, program, amount):
    """يمنح رصيدًا كافيًا للاستبدال عبر محرّك القيود."""
    from apps.ledger.services import apply_entry

    apply_entry(
        membership=membership,
        program=program,
        delta=Decimal(amount),
        reason="earn",
        actor=None,
    )


def redeem(membership, reward, *, used_by=None):
    """
    يُصدر كود استبدال عبر الخدمة، ويصرفه إن طُلب.

    عبر الخدمة لا بإنشاء الصف مباشرةً: الاستبدال يخصم رصيدًا ويكتب
    قيدًا، والصف المصنوع يدويًا يخلق استبدالًا بلا قيد يقابله —
    أي بالضبط الحالة التي يمنعها النظام.
    """
    from apps.ledger import services

    redemption = services.redeem_reward(membership=membership, reward=reward)
    if used_by is not None:
        services.use_redemption(code=redemption.code, staff_user=used_by)
    return redemption


def purchase(terminal, cashier, customer, amount="100", invoice="A-1"):
    txn = pos.create_transaction(
        code=codes.issue_code(terminal.id),
        customer=customer,
        invoice_amount=Decimal(amount),
        invoice_no=invoice,
    )
    pos.confirm_transaction(txn.id, staff_user=cashier)
    return txn


class TestRecentActivity:
    def test_newest_first(self, brand, terminal, cashier, program):
        purchase(terminal, cashier, factories.CustomerFactory(), invoice="A-1")
        latest = purchase(terminal, cashier, factories.CustomerFactory(), invoice="A-2")

        rows = reports.recent_activity(brand)

        assert rows[0]["id"] == str(latest.id)

    def test_carries_what_the_table_shows(self, brand, terminal, cashier, program):
        customer = factories.CustomerFactory(full_name="سارة عبد الله")
        purchase(terminal, cashier, customer, amount="250", invoice="A-3")

        row = reports.recent_activity(brand)[0]

        assert row["customer"] == "سارة عبد الله"
        assert row["branch"] == terminal.branch.name
        assert row["cashier"] == cashier.user.full_name
        assert row["amount"] == "250.00"
        assert row["status"] == Transaction.STATUS_CONFIRMED

    def test_delta_is_what_this_transaction_moved(self, brand, terminal, cashier, program):
        """
        «الأثر» في الجدول = قيود هذه العملية وحدها.

        مكافأة الانضمام تُمنح في نفس اللحظة لكنها **ليست** قيدًا
        على العملية: هي أثر التسجيل لا أثر الشراء، ويربطها المحرّك
        بالعضوية مباشرةً. ضمّها هنا كان سيجعل عكس فاتورة يبدو كأنه
        يسحب مكافأة الانضمام أيضًا — وهو ما لا يحدث ولا يجب أن يبدو
        أنه يحدث.

        العميل يرى الاثنين في سجلّه؛ التاجر يرى هنا ما فعلته الفاتورة.
        """
        program.rule.welcome_bonus = 50
        program.rule.save(update_fields=["welcome_bonus"])

        purchase(terminal, cashier, factories.CustomerFactory(), amount="100", invoice="A-4")

        row = reports.recent_activity(brand)[0]

        assert Decimal(row["delta"]) == Decimal("100.00")

    def test_a_visitor_without_a_name_is_labelled(self, brand, terminal, cashier, program):
        purchase(terminal, cashier, factories.CustomerFactory(full_name=""), invoice="A-5")

        assert reports.recent_activity(brand)[0]["customer"]

    def test_another_brand_never_appears(self, brand, terminal, cashier, program):
        purchase(terminal, cashier, factories.CustomerFactory(), invoice="A-6")

        assert reports.recent_activity(factories.BrandFactory()) == []

    def test_limit_is_respected(self, brand, terminal, cashier, program):
        for index in range(5):
            purchase(terminal, cashier, factories.CustomerFactory(), invoice=f"A-L{index}")

        assert len(reports.recent_activity(brand, limit=3)) == 3

    def test_endpoint_is_closed_to_cashiers(self, cashier, terminal, program):
        """اسم العميل بجوار اسم الكاشير ربط لا يخصّ كاشيرًا يرى زملاءه."""
        response = client_for(cashier).get(reverse("ledger:activity"))

        assert response.status_code == 403

    def test_endpoint_serves_managers(self, manager, terminal, cashier, program):
        purchase(terminal, cashier, factories.CustomerFactory(), invoice="A-7")

        body = client_for(manager).get(reverse("ledger:activity")).json()

        assert len(body["activity"]) == 1

    def test_endpoint_caps_a_silly_limit(self, manager):
        response = client_for(manager).get(reverse("ledger:activity"), {"limit": "9999"})

        assert response.status_code == 200


class TestCashierShift:
    def test_counts_only_today(self, terminal, cashier, program):
        old = purchase(terminal, cashier, factories.CustomerFactory(), invoice="S-1")
        Transaction.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timezone.timedelta(days=2)
        )
        purchase(terminal, cashier, factories.CustomerFactory(), invoice="S-2")

        assert reports.cashier_shift(cashier)["transactions"] == 1

    def test_counts_only_this_cashier(self, branch, terminal, cashier, program):
        other = factories.StaffUserFactory(branch=branch)
        purchase(terminal, other, factories.CustomerFactory(), invoice="S-3")

        assert reports.cashier_shift(cashier)["transactions"] == 0

    def test_pending_is_not_counted(self, terminal, cashier, program):
        """عملية لم تُؤكَّد ليست إنجازًا — الكاشير لم يُنهِها بعد."""
        pos.create_transaction(
            code=codes.issue_code(terminal.id),
            customer=factories.CustomerFactory(),
            invoice_amount=Decimal("100"),
            invoice_no="S-4",
        )

        assert reports.cashier_shift(cashier)["transactions"] == 0

    def test_distinct_customers(self, terminal, cashier, program):
        customer = factories.CustomerFactory()
        purchase(terminal, cashier, customer, invoice="S-5")
        purchase(terminal, cashier, customer, invoice="S-6")

        shift = reports.cashier_shift(cashier)

        assert shift["transactions"] == 2
        assert shift["customers"] == 1

    def test_endpoint_serves_the_cashier_themself(self, cashier, terminal, program):
        purchase(terminal, cashier, factories.CustomerFactory(), invoice="S-7")

        body = client_for(cashier).get(reverse("ledger:shift")).json()

        assert body["transactions"] == 1
        assert body["staff_name"] == cashier.user.full_name
        assert body["branch_name"] == cashier.branch.name


class TestRewardUsage:
    def test_counts_used_redemptions(self, brand, program, membership, cashier):
        earn(membership, program, "50")
        reward = factories.RewardFactory(program=program, cost_amount=Decimal("10"))

        redeem(membership, reward, used_by=cashier)

        assert reports.reward_usage(brand)[str(reward.id)] == 1

    def test_pending_code_is_not_a_redemption(self, brand, program, membership):
        """
        كود أُصدر ولم يُستعمل ليس استبدالًا: عدّه يجعل المكافأة تبدو
        رائجة وهي لم تُسلَّم قط، فيظن التاجر أن التكلفة عليه أعلى
        مما هي.
        """
        earn(membership, program, "50")
        reward = factories.RewardFactory(program=program, cost_amount=Decimal("10"))

        redeem(membership, reward)

        assert reports.reward_usage(brand) == {}

    def test_unused_reward_is_absent_not_zero(self, brand, program):
        factories.RewardFactory(program=program, cost_amount=Decimal("10"))

        assert reports.reward_usage(brand) == {}

    def test_list_endpoint_carries_the_count(self, manager, program, membership, cashier):
        earn(membership, program, "50")
        reward = factories.RewardFactory(program=program, cost_amount=Decimal("10"))
        redeem(membership, reward, used_by=cashier)

        rows = client_for(manager).get(reverse("loyalty:rewards")).json()

        assert rows[0]["redeemed_count"] == 1
