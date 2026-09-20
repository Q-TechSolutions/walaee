"""
رصيد الرسائل وحدود الباقات.

رصيد الرسائل مال حقيقي دفعه التاجر، فيخضع لنفس صرامة محرك القيود:
سجل append-only، قفل على اللقطة، ولا رصيد سالب.
"""

from decimal import Decimal
from threading import Barrier, Thread

import pytest
from django.db import connections

from apps.billing.models import Invoice, MessageCredit, MessageWallet, Plan, Subscription
from apps.billing.services import (
    BillingError,
    FeatureNotInPlan,
    InsufficientCredits,
    PlanLimitReached,
    apply_credit,
    check_limit,
    get_subscription,
    grant_monthly_credits,
    issue_invoice,
    mark_invoice_paid,
    refund_credits,
    require_feature,
    spend_credits,
    wallet_balance,
)
from tests import factories

pytestmark = pytest.mark.django_db


@pytest.fixture
def organization(db):
    return factories.OrganizationFactory()


class TestSubscription:
    def test_created_on_demand_as_free(self, organization):
        subscription = get_subscription(organization)

        assert subscription.plan == Plan.FREE
        assert subscription.status == Subscription.STATUS_TRIAL

    def test_returns_same_subscription(self, organization):
        first = get_subscription(organization)
        second = get_subscription(organization)

        assert first.id == second.id
        assert Subscription.objects.filter(organization=organization).count() == 1

    def test_cancelled_is_not_served(self, organization):
        subscription = get_subscription(organization)
        subscription.status = Subscription.STATUS_CANCELLED
        subscription.save(update_fields=["status"])

        assert subscription.is_serving is False

    def test_past_due_is_still_served(self, organization):
        """
        المتأخر سدادًا يُخدَم عمدًا — قطع الخدمة قرار بشري.
        عميل واقف عند الصندوق لا يجب أن يُحرم نقاطه بسبب تأخر فاتورة.
        """
        subscription = get_subscription(organization)
        subscription.status = Subscription.STATUS_PAST_DUE
        subscription.save(update_fields=["status"])

        assert subscription.is_serving is True


class TestPlanLimits:
    def test_free_plan_blocks_second_branch(self, organization):
        with pytest.raises(PlanLimitReached):
            check_limit(organization, "max_branches", current=1)

    def test_below_limit_passes(self, organization):
        check_limit(organization, "max_branches", current=0)

    def test_chain_plan_has_no_branch_limit(self, organization):
        subscription = get_subscription(organization)
        subscription.plan = Plan.CHAIN
        subscription.save(update_fields=["plan"])

        check_limit(organization, "max_branches", current=10_000)

    def test_campaigns_blocked_on_free(self, organization):
        with pytest.raises(FeatureNotInPlan):
            require_feature(organization, "campaigns_enabled")

    def test_campaigns_allowed_on_starter(self, organization):
        subscription = get_subscription(organization)
        subscription.plan = Plan.STARTER
        subscription.save(update_fields=["plan"])

        require_feature(organization, "campaigns_enabled")


class TestMessageCredits:
    def test_topup_then_spend(self, organization):
        apply_credit(organization=organization, delta=100, reason=MessageCredit.REASON_TOPUP)
        spend_credits(organization=organization, count=30)

        assert wallet_balance(organization) == 70

    def test_cannot_overdraw(self, organization):
        apply_credit(organization=organization, delta=10, reason=MessageCredit.REASON_TOPUP)

        with pytest.raises(InsufficientCredits):
            spend_credits(organization=organization, count=50)

        assert wallet_balance(organization) == 10

    def test_zero_delta_rejected(self, organization):
        with pytest.raises(BillingError):
            apply_credit(organization=organization, delta=0, reason=MessageCredit.REASON_TOPUP)

    def test_refund_restores_balance(self, organization):
        apply_credit(organization=organization, delta=100, reason=MessageCredit.REASON_TOPUP)
        spend_credits(organization=organization, count=40)
        refund_credits(organization=organization, count=10)

        assert wallet_balance(organization) == 70

    def test_credits_are_append_only(self, organization):
        from apps.common.models import AppendOnlyViolation

        credit = apply_credit(
            organization=organization, delta=50, reason=MessageCredit.REASON_TOPUP
        )
        credit.delta = 9999

        with pytest.raises(AppendOnlyViolation):
            credit.save()

    def test_history_matches_snapshot(self, organization):
        from django.db.models import Sum

        for amount in (100, -20, -30, 10):
            reason = MessageCredit.REASON_TOPUP if amount > 0 else MessageCredit.REASON_SEND
            apply_credit(organization=organization, delta=amount, reason=reason)

        total = MessageCredit.objects.filter(organization=organization).aggregate(
            total=Sum("delta")
        )["total"]

        assert total == wallet_balance(organization) == 60

    def test_monthly_grant_by_plan(self, organization):
        subscription = get_subscription(organization)
        subscription.plan = Plan.GROWTH
        subscription.save(update_fields=["plan"])

        grant_monthly_credits(subscription)

        assert wallet_balance(organization) == 3_000

    def test_free_plan_grants_nothing(self, organization):
        subscription = get_subscription(organization)

        assert grant_monthly_credits(subscription) is None
        assert wallet_balance(organization) == 0

    def test_empty_wallet_reads_zero(self, organization):
        assert wallet_balance(organization) == 0


class TestInvoices:
    def test_issue_advances_period_and_grants(self, organization):
        subscription = get_subscription(organization)
        subscription.plan = Plan.STARTER
        subscription.save(update_fields=["plan"])
        original_end = subscription.current_period_end

        invoice = issue_invoice(subscription)
        subscription.refresh_from_db()

        assert invoice.amount == Decimal("450")
        assert invoice.status == Invoice.STATUS_ISSUED
        assert subscription.current_period_start == original_end
        assert subscription.current_period_end > original_end
        # المنحة الشهرية تُصرف مع الفاتورة
        assert wallet_balance(organization) == 500

    def test_number_is_sequential(self, organization):
        subscription = get_subscription(organization)

        first = issue_invoice(subscription)
        second = issue_invoice(subscription)

        assert first.number != second.number
        assert first.number.startswith("WL-")
        assert int(second.number.rsplit("-", 1)[1]) == int(first.number.rsplit("-", 1)[1]) + 1

    def test_payment_activates_subscription(self, organization):
        subscription = get_subscription(organization)
        invoice = issue_invoice(subscription)

        mark_invoice_paid(invoice, reference="TRX-991")
        subscription.refresh_from_db()

        assert invoice.status == Invoice.STATUS_PAID
        assert invoice.payment_ref == "TRX-991"
        assert subscription.status == Subscription.STATUS_ACTIVE

    def test_double_payment_rejected(self, organization):
        subscription = get_subscription(organization)
        invoice = issue_invoice(subscription)
        mark_invoice_paid(invoice)

        with pytest.raises(BillingError) as exc:
            mark_invoice_paid(invoice)
        assert exc.value.code == "already_paid"


@pytest.mark.django_db(transaction=True)
@pytest.mark.concurrency
class TestCreditConcurrency:
    def test_parallel_spends_cannot_overdraw(self):
        """
        رصيد ١٠٠ وثلاث محاولات خصم ٨٠ متزامنة.

        نفس سيناريو محرك القيود: بلا قفل تقرأ الثلاث ١٠٠ وتمرّ،
        فينتهي رصيد التاجر إلى سالب وهو مال دفعه فعلًا.
        """
        organization = factories.OrganizationFactory()
        apply_credit(organization=organization, delta=100, reason=MessageCredit.REASON_TOPUP)

        barrier = Barrier(3, timeout=10)
        errors = []

        def worker():
            try:
                barrier.wait()
                spend_credits(organization=organization, count=80)
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)
            finally:
                connections.close_all()

        threads = [Thread(target=worker) for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)

        assert MessageWallet.objects.get(organization=organization).balance == 20
        assert len(errors) == 2
        assert all(isinstance(e, InsufficientCredits) for e in errors)
