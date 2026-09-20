"""
مراجعة الاحتيال والمهام المجدولة.

المبدأ المختبَر هنا: **النظام يرفع راية ولا يحكم.** رفض العملية
يعكس قيودها بقيود مضادة لا بحذفها — فيبقى التاريخ كاملًا ويظل
الرصيد قابلًا للتفسير.
"""

from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.fraud.models import FraudSignal
from apps.ledger.models import LedgerEntry, Transaction
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
def flagged(terminal, branch, program):
    """عملية مؤكّدة عليها إشارة خطورة عالية."""
    cashier = factories.StaffUserFactory(branch=branch)
    customer = factories.CustomerFactory(phone=cashier.user.phone)

    code = codes.issue_code(terminal.id)
    txn = services.create_transaction(
        code=code, customer=customer, invoice_amount=Decimal("200"), invoice_no="FR-1"
    )
    services.confirm_transaction(txn.id, staff_user=cashier)

    return FraudSignal.objects.get(transaction=txn, rule_code="staff_self_transaction")


class TestSignalList:
    def test_high_severity_first(self, owner_api, flagged, terminal, branch, program):
        cashier = factories.StaffUserFactory(branch=branch)
        customer = factories.CustomerFactory()
        code = codes.issue_code(terminal.id)
        txn = services.create_transaction(
            code=code, customer=customer, invoice_amount=Decimal("1000"), invoice_no="FR-2"
        )
        services.confirm_transaction(txn.id, staff_user=cashier)

        body = owner_api.get(reverse("fraud:signals")).json()

        assert len(body) >= 2
        assert body[0]["severity"] == "high"

    def test_labels_are_arabic(self, owner_api, flagged):
        body = owner_api.get(reverse("fraud:signals")).json()

        assert body[0]["rule_label"] == "الكاشير يمنح نقاطًا لرقمه"

    def test_shows_context(self, owner_api, flagged):
        body = owner_api.get(reverse("fraud:signals")).json()

        assert body[0]["invoice_no"] == "FR-1"
        assert body[0]["invoice_amount"] == "200.00"
        assert body[0]["branch_name"]

    def test_other_brand_signals_invisible(self, owner_api, flagged):
        other_terminal = factories.TerminalFactory()
        other_cashier = factories.StaffUserFactory(branch=other_terminal.branch)
        other_program = factories.LoyaltyProgramFactory(brand=other_terminal.branch.brand)
        factories.ProgramRuleFactory(program=other_program)

        code = codes.issue_code(other_terminal.id)
        txn = services.create_transaction(
            code=code,
            customer=factories.CustomerFactory(phone=other_cashier.user.phone),
            invoice_amount=Decimal("100"),
            invoice_no="OTHER-1",
        )
        services.confirm_transaction(txn.id, staff_user=other_cashier)

        body = owner_api.get(reverse("fraud:signals")).json()

        assert all(row["invoice_no"] != "OTHER-1" for row in body)


class TestResolve:
    def test_accept_closes_without_touching_balance(self, owner_api, flagged, program):
        before = Balance.objects.get(program=program).amount

        response = owner_api.post(
            reverse("fraud:resolve", args=[flagged.id]),
            {"action": "accept"},
            format="json",
        )

        assert response.status_code == 200
        assert response.json()["status"] == FraudSignal.STATUS_ACCEPTED
        assert response.json()["reversed_entries"] == []
        assert Balance.objects.get(program=program).amount == before

    def test_reject_reverses_by_counter_entry(self, owner_api, flagged, program):
        txn = flagged.transaction
        original_entries = list(txn.entries.values_list("id", flat=True))

        response = owner_api.post(
            reverse("fraud:resolve", args=[flagged.id]),
            {"action": "reject"},
            format="json",
        )

        assert response.status_code == 200
        assert len(response.json()["reversed_entries"]) == len(original_entries)

        # الرصيد عاد إلى الصفر
        assert Balance.objects.get(program=program).amount == Decimal("0")

        # القيود الأصلية لم تُحذف — التاريخ كامل
        assert LedgerEntry.objects.filter(id__in=original_entries).count() == len(original_entries)
        assert LedgerEntry.objects.filter(reason=LedgerEntry.REASON_REVERSE).count() == len(
            original_entries
        )

        txn.refresh_from_db()
        assert txn.status == Transaction.STATUS_REVERSED

    def test_double_review_rejected(self, owner_api, flagged):
        owner_api.post(
            reverse("fraud:resolve", args=[flagged.id]),
            {"action": "accept"},
            format="json",
        )

        response = owner_api.post(
            reverse("fraud:resolve", args=[flagged.id]),
            {"action": "accept"},
            format="json",
        )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "already_reviewed"

    def test_invalid_action_rejected(self, owner_api, flagged):
        response = owner_api.post(
            reverse("fraud:resolve", args=[flagged.id]),
            {"action": "explode"},
            format="json",
        )

        assert response.status_code == 400

    def test_manager_cannot_resolve(self, branch, flagged):
        manager = factories.StaffUserFactory(branch=branch, role=StaffUser.ROLE_MANAGER)
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(manager.user).access_token}"
        )

        response = client.post(
            reverse("fraud:resolve", args=[flagged.id]),
            {"action": "reject"},
            format="json",
        )

        assert response.status_code == 403
