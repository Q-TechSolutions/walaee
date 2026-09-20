"""
تقارير لوحة التاجر.

هذه الأرقام يبني عليها التاجر قرارات حقيقية — يرفع معدل المنح أو
يغلق فرعًا. رقم خاطئ هنا لا يُسقط النظام، وهذا بالضبط ما يجعله
أخطر: يعيش شهورًا بلا أن يلاحظه أحد.
"""

from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.ledger import reports
from apps.ledger.models import LedgerEntry
from apps.ledger.services import apply_entry
from apps.ledger.tasks import expire_balances, notify_expiring, verify_integrity
from apps.loyalty.models import Balance
from apps.pos import codes, services
from apps.tenancy.models import StaffUser
from tests import factories

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner(branch):
    return factories.StaffUserFactory(branch=branch, role=StaffUser.ROLE_OWNER)


@pytest.fixture
def owner_api(owner):
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(owner.user).access_token}"
    )
    return client


@pytest.fixture
def manager(branch):
    return factories.StaffUserFactory(branch=branch, role=StaffUser.ROLE_MANAGER)


@pytest.fixture
def manager_api(manager):
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(manager.user).access_token}"
    )
    return client


def _purchase(terminal, cashier, customer, amount, invoice_no):
    code = codes.issue_code(terminal.id)
    txn = services.create_transaction(
        code=code,
        customer=customer,
        invoice_amount=Decimal(amount),
        invoice_no=invoice_no,
    )
    services.confirm_transaction(txn.id, staff_user=cashier)
    return txn


class TestDailySeries:
    def test_groups_by_day(self, brand, terminal, cashier, program):
        customer = factories.CustomerFactory()
        _purchase(terminal, cashier, customer, "100", "S-1")
        _purchase(terminal, cashier, customer, "50", "S-2")

        series = reports.daily_series(brand)

        assert len(series) == 1
        assert series[0]["transactions"] == 2
        assert series[0]["revenue"] == "150.00"

    def test_empty_brand_returns_empty_list(self, brand):
        assert reports.daily_series(brand) == []


class TestCustomerSegments:
    def test_counts_by_activity_window(self, brand, terminal, cashier, program):
        active = factories.CustomerFactory(consent_at=timezone.now())
        _purchase(terminal, cashier, active, "100", "SEG-1")

        # عميل انضم ولم يشترِ قط
        factories.MembershipFactory(brand=brand)

        result = reports.customer_segments(brand)

        assert result["total"] == 2
        assert result["active_30d"] == 1
        assert result["dormant_90d"] == 1
        assert result["with_consent"] == 1

    def test_new_within_seven_days(self, brand):
        factories.MembershipFactory(brand=brand)

        assert reports.customer_segments(brand)["new_7d"] == 1

    def test_deleted_customers_excluded(self, brand):
        membership = factories.MembershipFactory(brand=brand)
        membership.customer.deleted_at = timezone.now()
        membership.customer.save(update_fields=["deleted_at"])

        assert reports.customer_segments(brand)["total"] == 0


class TestTopCustomers:
    def test_sorted_by_spend(self, brand, terminal, cashier, program):
        big = factories.CustomerFactory(full_name="كبير")
        small = factories.CustomerFactory(full_name="صغير")
        _purchase(terminal, cashier, big, "500", "T-1")
        _purchase(terminal, cashier, small, "80", "T-2")

        rows = reports.top_customers(brand)

        assert [row["name"] for row in rows] == ["كبير", "صغير"]
        assert rows[0]["total_spend"] == "500.00"
        assert rows[0]["visits"] == 1

    def test_respects_limit(self, brand, terminal, cashier, program):
        for index in range(3):
            _purchase(terminal, cashier, factories.CustomerFactory(), "10", f"L-{index}")

        assert len(reports.top_customers(brand, limit=2)) == 2

    def test_empty_brand(self, brand):
        assert reports.top_customers(brand) == []


class TestBranchPerformance:
    def test_compares_branches(self, brand, program):
        first = factories.BranchFactory(brand=brand, name="الأول")
        second = factories.BranchFactory(brand=brand, name="الثاني")
        t1 = factories.TerminalFactory(branch=first)
        t2 = factories.TerminalFactory(branch=second)
        c1 = factories.StaffUserFactory(branch=first)
        c2 = factories.StaffUserFactory(branch=second)

        _purchase(t1, c1, factories.CustomerFactory(), "400", "B-1")
        _purchase(t2, c2, factories.CustomerFactory(), "100", "B-2")

        rows = reports.branch_performance(brand)

        assert [row["branch_name"] for row in rows] == ["الأول", "الثاني"]
        assert rows[0]["revenue"] == "400.00"
        assert rows[0]["customers"] == 1


class TestProgramPerformance:
    def test_granted_versus_redeemed(self, brand, program, membership):
        apply_entry(membership=membership, program=program, delta=Decimal("200"), reason="earn")
        apply_entry(
            membership=membership,
            program=program,
            delta=Decimal("-50"),
            reason=LedgerEntry.REASON_REDEEM,
        )

        rows = reports.program_performance(brand)

        assert rows[0]["granted"] == "200.00"
        assert rows[0]["redeemed"] == "50.00"
        assert rows[0]["redemption_rate_pct"] == 25.0

    def test_expired_counted_separately(self, brand, program, membership):
        apply_entry(membership=membership, program=program, delta=Decimal("100"), reason="earn")
        apply_entry(
            membership=membership,
            program=program,
            delta=Decimal("-100"),
            reason=LedgerEntry.REASON_EXPIRE,
        )

        rows = reports.program_performance(brand)

        assert rows[0]["expired"] == "100.00"
        assert rows[0]["redeemed"] == "0"

    def test_no_activity_means_zero_rate(self, brand, program):
        rows = reports.program_performance(brand)

        assert rows[0]["granted"] == "0"
        assert rows[0]["redemption_rate_pct"] == 0.0


class TestReportEndpoints:
    @pytest.mark.parametrize("kind", ["top-customers", "branches", "programs"])
    def test_each_kind_returns_rows(self, owner_api, kind, program):
        response = owner_api.get(reverse("ledger:report", args=[kind]))

        assert response.status_code == 200
        assert response.json()["kind"] == kind
        assert "rows" in response.json()

    def test_unknown_kind_lists_available(self, owner_api):
        response = owner_api.get(reverse("ledger:report", args=["nonsense"]))

        assert response.status_code == 404
        body = response.json()["error"]
        assert body["code"] == "unknown_report"
        assert "programs" in body["details"]["available"]

    def test_export_requires_paid_plan(self, owner_api):
        """القراءة على الشاشة مجانية — التصدير ميزة مدفوعة."""
        response = owner_api.get(reverse("ledger:report", args=["programs"]), {"export": "1"})

        assert response.status_code == 402
        assert response.json()["error"]["code"] == "feature_not_in_plan"

    def test_export_allowed_on_paid_plan(self, owner_api, brand):
        from apps.billing.models import Plan
        from apps.billing.services import get_subscription

        subscription = get_subscription(brand.organization)
        subscription.plan = Plan.STARTER
        subscription.save(update_fields=["plan"])

        response = owner_api.get(reverse("ledger:report", args=["programs"]), {"export": "1"})

        assert response.status_code == 200

    def test_series_endpoint(self, owner_api, terminal, cashier, program):
        _purchase(terminal, cashier, factories.CustomerFactory(), "90", "SE-1")

        body = owner_api.get(reverse("ledger:series")).json()

        assert body["series"][0]["revenue"] == "90.00"

    def test_segments_endpoint(self, owner_api, brand):
        factories.MembershipFactory(brand=brand)

        body = owner_api.get(reverse("ledger:segments")).json()

        assert body["total"] == 1


class TestManualReversal:
    def test_owner_reverses_entry(self, owner_api, membership, program):
        entry = apply_entry(
            membership=membership, program=program, delta=Decimal("60"), reason="earn"
        )

        response = owner_api.post(reverse("ledger:reverse", args=[entry.id]))

        assert response.status_code == 200
        body = response.json()
        assert body["delta"] == "-60.00"
        assert body["balance_after"] == "0.00"

    def test_double_reversal_rejected(self, owner_api, membership, program):
        entry = apply_entry(
            membership=membership, program=program, delta=Decimal("60"), reason="earn"
        )
        owner_api.post(reverse("ledger:reverse", args=[entry.id]))

        response = owner_api.post(reverse("ledger:reverse", args=[entry.id]))

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "already_reversed"

    def test_manager_cannot_reverse(self, branch, membership, program):
        manager = factories.StaffUserFactory(branch=branch, role=StaffUser.ROLE_MANAGER)
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(manager.user).access_token}"
        )
        entry = apply_entry(
            membership=membership, program=program, delta=Decimal("10"), reason="earn"
        )

        assert client.post(reverse("ledger:reverse", args=[entry.id])).status_code == 403


class TestDashboard:
    def test_reports_real_numbers(self, manager_api, terminal, cashier, customer, program):
        from apps.pos import codes, services

        code = codes.issue_code(terminal.id)
        txn = services.create_transaction(
            code=code,
            customer=customer,
            invoice_amount=Decimal("300"),
            invoice_no="D-1",
        )
        services.confirm_transaction(txn.id, staff_user=cashier)

        body = manager_api.get(reverse("ledger:dashboard")).json()

        assert body["transactions"]["count"] == 1
        assert body["revenue"]["total"] == "300.00"
        assert body["customers"]["total"] == 1
        assert body["liability"]["total_units"] == "300.00"

    def test_empty_brand_does_not_crash(self, manager_api):
        body = manager_api.get(reverse("ledger:dashboard")).json()

        assert body["transactions"]["count"] == 0
        assert body["revenue"]["total"] == "0"
        # لا فترة سابقة يُقاس عليها
        assert body["transactions"]["change_pct"] is None

    def test_days_is_clamped(self, manager_api):
        body = manager_api.get(reverse("ledger:dashboard"), {"days": "99999"}).json()
        assert body["period_days"] == 365

        body = manager_api.get(reverse("ledger:dashboard"), {"days": "abc"}).json()
        assert body["period_days"] == 30


class TestLiability:
    def test_valued_by_cheapest_reward(self, owner_api, brand, program, customer):
        """
        ١٠٠ نقطة تساوي قهوة تكلّف التاجر ١٨ جنيهًا،
        فقيمة النقطة ٠٫١٨ و٥٠٠ نقطة = ٩٠ جنيهًا.
        """
        factories.RewardFactory(
            program=program, cost_amount=Decimal("100"), merchant_cost=Decimal("18")
        )
        membership = factories.MembershipFactory(customer=customer, brand=brand)
        apply_entry(membership=membership, program=program, delta=Decimal("500"), reason="earn")

        body = owner_api.get(reverse("ledger:liability")).json()

        assert body["total_units"] == "500.00"
        assert body["estimated_value"] == "90.00"
        assert body["currency"] == "EGP"

    def test_no_reward_means_no_value(self, owner_api, brand, program, customer):
        membership = factories.MembershipFactory(customer=customer, brand=brand)
        apply_entry(membership=membership, program=program, delta=Decimal("500"), reason="earn")

        body = owner_api.get(reverse("ledger:liability")).json()

        assert body["total_units"] == "500.00"
        assert body["estimated_value"] == "0.00"


# ═══════════════════════ الحوكمة وحدود الباقة ═══════════════════════


class TestExpiryTasks:
    def test_expire_writes_explicit_entry(self, membership, program):
        """
        انتهاء الصلاحية حدث مالي يظهر في كشف حساب العميل.
        تصفير الرصيد مباشرة يجعل نقاطه تختفي بلا تفسير.
        """
        apply_entry(membership=membership, program=program, delta=Decimal("120"), reason="earn")
        Balance.objects.filter(membership=membership).update(
            expires_at=timezone.now() - timezone.timedelta(days=1)
        )

        assert expire_balances() == 1

        assert Balance.objects.get(membership=membership).amount == Decimal("0")
        entry = LedgerEntry.objects.get(reason=LedgerEntry.REASON_EXPIRE)
        assert entry.delta == Decimal("-120")

    def test_future_expiry_untouched(self, membership, program):
        apply_entry(membership=membership, program=program, delta=Decimal("50"), reason="earn")

        assert expire_balances() == 0
        assert Balance.objects.get(membership=membership).amount == Decimal("50")

    def test_zero_balance_skipped(self, membership, program):
        Balance.objects.create(
            membership=membership,
            program=program,
            amount=Decimal("0"),
            expires_at=timezone.now() - timezone.timedelta(days=1),
        )

        assert expire_balances() == 0
        assert LedgerEntry.objects.count() == 0

    def test_warning_sent_on_free_channel(self, brand, program):
        customer = factories.CustomerFactory(
            consent_at=timezone.now(),
            push_subscription={"endpoint": "https://push.example/x"},
        )
        membership = factories.MembershipFactory(customer=customer, brand=brand)
        apply_entry(membership=membership, program=program, delta=Decimal("200"), reason="earn")
        Balance.objects.filter(membership=membership).update(
            expires_at=timezone.now() + timezone.timedelta(days=29, hours=12)
        )

        assert notify_expiring() == 1

    def test_no_warning_without_push(self, brand, program, membership):
        """بلا إشعار مجاني لا يُرسَل تنبيه — لا يُخصم رصيد التاجر."""
        apply_entry(membership=membership, program=program, delta=Decimal("200"), reason="earn")
        Balance.objects.filter(membership=membership).update(
            expires_at=timezone.now() + timezone.timedelta(days=29, hours=12)
        )

        assert notify_expiring() == 0


class TestIntegrityTask:
    def test_clean_ledger_reports_no_drift(self, membership, program):
        apply_entry(membership=membership, program=program, delta=Decimal("40"), reason="earn")

        result = verify_integrity()

        assert result["drifted"] == 0
        assert result["checked"] == 1

    def test_detects_tampered_snapshot(self, membership, program):
        apply_entry(membership=membership, program=program, delta=Decimal("40"), reason="earn")
        Balance.objects.filter(membership=membership).update(amount=Decimal("999"))

        result = verify_integrity()

        assert result["drifted"] == 1
        assert result["details"][0]["snapshot"] == "999.00"
        assert result["details"][0]["ledger_total"] == "40.00"
