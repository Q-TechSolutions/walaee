"""
اختبارات محرك القيود.

التغطية هنا ١٠٠٪ إلزامية وشرط للدمج — docs/architecture/testing.md
"""

from decimal import Decimal

import pytest

from apps.ledger.models import LedgerEntry
from apps.ledger.services import (
    AlreadyReversed,
    DailyCapExceeded,
    InsufficientBalance,
    LedgerError,
    MembershipBlocked,
    apply_entry,
    grant_welcome_bonus,
    reverse_entry,
    verify_balance,
)
from apps.loyalty.models import Balance, Membership

pytestmark = pytest.mark.django_db


def _earn(membership, program, amount):
    return apply_entry(
        membership=membership,
        program=program,
        delta=Decimal(amount),
        reason=LedgerEntry.REASON_EARN,
    )


class TestApplyEntry:
    def test_first_entry_creates_balance(self, membership, program):
        entry = _earn(membership, program, 50)

        balance = Balance.objects.get(membership=membership, program=program)
        assert balance.amount == Decimal("50")
        assert entry.balance_after == Decimal("50")

    def test_entries_accumulate(self, membership, program):
        _earn(membership, program, 30)
        second = _earn(membership, program, 20)

        balance = Balance.objects.get(membership=membership, program=program)
        assert balance.amount == Decimal("50")
        assert second.balance_after == Decimal("50")

    def test_zero_delta_rejected(self, membership, program):
        with pytest.raises(LedgerError):
            _earn(membership, program, 0)

    def test_blocked_membership_rejected(self, membership, program):
        membership.status = Membership.STATUS_BLOCKED
        membership.save(update_fields=["status"])

        with pytest.raises(MembershipBlocked):
            _earn(membership, program, 10)

    def test_negative_balance_rejected(self, membership, program):
        _earn(membership, program, 10)

        with pytest.raises(InsufficientBalance):
            apply_entry(
                membership=membership,
                program=program,
                delta=Decimal("-50"),
                reason=LedgerEntry.REASON_REDEEM,
            )

        # لم يُكتب أي قيد للمحاولة الفاشلة
        assert LedgerEntry.objects.filter(membership=membership).count() == 1

    def test_expiry_set_on_earn(self, membership, program):
        _earn(membership, program, 10)

        balance = Balance.objects.get(membership=membership, program=program)
        assert balance.expires_at is not None

    def test_audit_log_written(self, membership, program):
        from apps.audit.models import AuditLog

        entry = _earn(membership, program, 15)

        log = AuditLog.objects.filter(entity_id=str(entry.id)).first()
        assert log is not None
        assert log.action == "ledger.earn"
        assert log.after["delta"] == "15"


class TestDailyCap:
    def test_cap_blocks_excess(self, membership, program):
        rule = program.rule
        rule.max_per_day = Decimal("100")
        rule.save(update_fields=["max_per_day"])

        _earn(membership, program, 80)

        with pytest.raises(DailyCapExceeded):
            _earn(membership, program, 30)

    def test_cap_allows_exactly_at_limit(self, membership, program):
        rule = program.rule
        rule.max_per_day = Decimal("100")
        rule.save(update_fields=["max_per_day"])

        _earn(membership, program, 60)
        _earn(membership, program, 40)

        balance = Balance.objects.get(membership=membership, program=program)
        assert balance.amount == Decimal("100")

    def test_cap_ignores_redemptions(self, membership, program):
        """الاستبدال لا يُحسب ضمن السقف اليومي للمنح."""
        rule = program.rule
        rule.max_per_day = Decimal("100")
        rule.save(update_fields=["max_per_day"])

        _earn(membership, program, 100)
        apply_entry(
            membership=membership,
            program=program,
            delta=Decimal("-50"),
            reason=LedgerEntry.REASON_REDEEM,
        )

        # السقف لا يزال مستهلكًا رغم الخصم — المنح اليومي هو المقيَّد
        with pytest.raises(DailyCapExceeded):
            _earn(membership, program, 10)


class TestReversal:
    def test_reverse_creates_opposite_entry(self, membership, program):
        original = _earn(membership, program, 40)
        reversal = reverse_entry(original)

        assert reversal.delta == Decimal("-40")
        assert reversal.reason == LedgerEntry.REASON_REVERSE
        assert reversal.reverses_id == original.id

        balance = Balance.objects.get(membership=membership, program=program)
        assert balance.amount == Decimal("0")

    def test_double_reversal_rejected(self, membership, program):
        original = _earn(membership, program, 40)
        reverse_entry(original)

        with pytest.raises(AlreadyReversed):
            reverse_entry(original)

    def test_original_entry_untouched(self, membership, program):
        original = _earn(membership, program, 40)
        reverse_entry(original)

        original.refresh_from_db()
        assert original.delta == Decimal("40")
        assert original.balance_after == Decimal("40")


class TestAppendOnly:
    def test_entry_cannot_be_updated(self, membership, program):
        from apps.common.models import AppendOnlyViolation

        entry = _earn(membership, program, 10)
        entry.delta = Decimal("999")

        with pytest.raises(AppendOnlyViolation):
            entry.save()

    def test_entry_cannot_be_deleted(self, membership, program):
        from apps.common.models import AppendOnlyViolation

        entry = _earn(membership, program, 10)

        with pytest.raises(AppendOnlyViolation):
            entry.delete()


class TestWelcomeBonus:
    def test_granted_once(self, membership, program):
        rule = program.rule
        rule.welcome_bonus = 25
        rule.save(update_fields=["welcome_bonus"])

        first = grant_welcome_bonus(membership=membership, program=program)
        second = grant_welcome_bonus(membership=membership, program=program)

        assert first is not None
        assert second is None
        assert Balance.objects.get(membership=membership, program=program).amount == Decimal("25")

    def test_zero_bonus_writes_nothing(self, membership, program):
        assert grant_welcome_bonus(membership=membership, program=program) is None
        assert LedgerEntry.objects.count() == 0


class TestVerifyBalance:
    def test_consistent_after_normal_flow(self, membership, program):
        _earn(membership, program, 30)
        _earn(membership, program, 20)

        result = verify_balance(membership, program)
        assert result["consistent"] is True
        assert result["drift"] == Decimal("0")

    def test_detects_drift(self, membership, program):
        _earn(membership, program, 30)

        # محاكاة مسار فاسد يكتب في الرصيد خارج المحرك
        Balance.objects.filter(membership=membership, program=program).update(amount=Decimal("999"))

        result = verify_balance(membership, program)
        assert result["consistent"] is False
        assert result["drift"] == Decimal("969")

    def test_empty_wallet_is_consistent(self, membership, program):
        result = verify_balance(membership, program)
        assert result["consistent"] is True
