"""اختبارات الاستبدال: من خصم الرصيد إلى صرف الكود عند الكاشير."""

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.ledger import services as ledger_services
from apps.ledger.models import LedgerEntry, Redemption, Transaction
from apps.ledger.services import (
    LedgerError,
    apply_entry,
    redeem_reward,
    use_redemption,
)
from apps.loyalty.models import Balance
from tests import factories

pytestmark = pytest.mark.django_db


@pytest.fixture
def funded_membership(membership, program):
    apply_entry(
        membership=membership,
        program=program,
        delta=Decimal("500"),
        reason=LedgerEntry.REASON_EARN,
    )
    return membership


@pytest.fixture
def reward(program):
    return factories.RewardFactory(program=program, cost_amount=Decimal("100"))


class TestRedeemReward:
    def test_deducts_balance_and_issues_code(self, funded_membership, reward, program):
        redemption = redeem_reward(membership=funded_membership, reward=reward)

        assert redemption.status == Redemption.STATUS_PENDING
        assert len(redemption.code) == 8
        assert redemption.expires_at > timezone.now()

        balance = Balance.objects.get(membership=funded_membership, program=program)
        assert balance.amount == Decimal("400")

        assert redemption.ledger_entry.delta == Decimal("-100")
        assert redemption.ledger_entry.reason == LedgerEntry.REASON_REDEEM

    def test_code_has_no_ambiguous_characters(self, funded_membership, reward):
        """الكود يُملى صوتيًا أحيانًا — O و 0 و I و 1 ممنوعة."""
        redemption = redeem_reward(membership=funded_membership, reward=reward)
        assert not set(redemption.code) & set("O0I1")

    def test_insufficient_balance_rejected(self, membership, reward):
        with pytest.raises(LedgerError) as exc:
            redeem_reward(membership=membership, reward=reward)
        assert exc.value.code == "insufficient_balance"

    def test_inactive_reward_rejected(self, funded_membership, reward):
        reward.is_active = False
        reward.save(update_fields=["is_active"])

        with pytest.raises(LedgerError):
            redeem_reward(membership=funded_membership, reward=reward)

    def test_out_of_stock_rejected(self, funded_membership, reward):
        reward.stock = 0
        reward.save(update_fields=["stock"])

        with pytest.raises(LedgerError):
            redeem_reward(membership=funded_membership, reward=reward)

    def test_stock_decremented(self, funded_membership, reward):
        reward.stock = 3
        reward.save(update_fields=["stock"])

        redeem_reward(membership=funded_membership, reward=reward)

        reward.refresh_from_db()
        assert reward.stock == 2

    def test_collision_retries_until_unique(self, funded_membership, reward, monkeypatch):
        """تصادم كود مع كود قائم يُعاد التوليد لا يفشل."""
        first = redeem_reward(membership=funded_membership, reward=reward)

        # المولّد يرجع كودًا مستخدمًا ثم كودًا فريدًا
        sequence = iter([first.code, "ZZ234567"])
        monkeypatch.setattr(ledger_services, "_generate_redemption_code", lambda: next(sequence))

        second = redeem_reward(membership=funded_membership, reward=reward)
        assert second.code == "ZZ234567"

    def test_reward_from_other_brand_rejected(self, funded_membership):
        other_program = factories.LoyaltyProgramFactory()
        factories.ProgramRuleFactory(program=other_program)
        foreign_reward = factories.RewardFactory(program=other_program)

        with pytest.raises(LedgerError):
            redeem_reward(membership=funded_membership, reward=foreign_reward)


class TestUseRedemption:
    def test_cashier_can_use_code(self, funded_membership, reward, branch, brand):
        funded_membership.brand = brand
        funded_membership.save(update_fields=["brand"])

        cashier = factories.StaffUserFactory(branch=branch)
        redemption = redeem_reward(membership=funded_membership, reward=reward)

        used = use_redemption(code=redemption.code, staff_user=cashier)

        assert used.status == Redemption.STATUS_USED
        assert used.used_at is not None
        assert used.used_by_staff_id == cashier.id

    def test_code_is_case_insensitive(self, funded_membership, reward, branch):
        cashier = factories.StaffUserFactory(branch=branch)
        redemption = redeem_reward(membership=funded_membership, reward=reward)

        used = use_redemption(code=redemption.code.lower(), staff_user=cashier)
        assert used.status == Redemption.STATUS_USED

    def test_second_use_rejected(self, funded_membership, reward, branch):
        cashier = factories.StaffUserFactory(branch=branch)
        redemption = redeem_reward(membership=funded_membership, reward=reward)

        use_redemption(code=redemption.code, staff_user=cashier)

        with pytest.raises(LedgerError) as exc:
            use_redemption(code=redemption.code, staff_user=cashier)
        assert exc.value.code == "already_used"

    def test_unknown_code_rejected(self, branch):
        cashier = factories.StaffUserFactory(branch=branch)

        with pytest.raises(LedgerError) as exc:
            use_redemption(code="ZZZZZZZZ", staff_user=cashier)
        assert exc.value.code == "redemption_not_found"

    def test_expired_code_rejected(self, funded_membership, reward, branch):
        cashier = factories.StaffUserFactory(branch=branch)
        redemption = redeem_reward(membership=funded_membership, reward=reward)

        redemption.expires_at = timezone.now() - timezone.timedelta(minutes=1)
        redemption.save(update_fields=["expires_at"])

        with pytest.raises(LedgerError) as exc:
            use_redemption(code=redemption.code, staff_user=cashier)
        assert exc.value.code == "redemption_expired"

        redemption.refresh_from_db()
        assert redemption.status == Redemption.STATUS_EXPIRED

    def test_cashier_from_other_brand_rejected(self, funded_membership, reward):
        """كود علامة «أ» لا يُصرف في متجر علامة «ب»."""
        other_branch = factories.BranchFactory()
        foreign_cashier = factories.StaffUserFactory(branch=other_branch)
        redemption = redeem_reward(membership=funded_membership, reward=reward)

        with pytest.raises(LedgerError) as exc:
            use_redemption(code=redemption.code, staff_user=foreign_cashier)
        assert exc.value.code == "wrong_brand"


class TestStringRepresentations:
    """يضمن أن أي سجل يظهر مقروءًا في لوحة الإدارة وسجلات التشغيل."""

    def test_transaction_str(self, terminal, customer):
        txn = Transaction.objects.create(
            terminal=terminal,
            customer=customer,
            invoice_no="INV-9",
            invoice_amount=Decimal("75"),
        )
        assert "INV-9" in str(txn)
        assert txn.brand_id == terminal.branch.brand_id

    def test_entry_str_shows_sign(self, membership, program):
        positive = apply_entry(
            membership=membership,
            program=program,
            delta=Decimal("10"),
            reason=LedgerEntry.REASON_EARN,
        )
        negative = apply_entry(
            membership=membership,
            program=program,
            delta=Decimal("-4"),
            reason=LedgerEntry.REASON_REDEEM,
        )
        assert str(positive).startswith("+")
        assert str(negative).startswith("-")

    def test_redemption_str(self, funded_membership, reward):
        redemption = redeem_reward(membership=funded_membership, reward=reward)
        assert redemption.code in str(redemption)
