"""
دورة «رمز ← مسح ← فاتورة ← تأكيد ← نقطة» كاملة.

هذا هو الطريق الذي يمر به كل جنيه في النظام — اختباره من طرفه
إلى طرفه يكشف ما لا تكشفه اختبارات الوحدة المعزولة.
"""

from decimal import Decimal

import pytest
from django.core.cache import cache
from django.core.exceptions import PermissionDenied

from apps.common.exceptions import CodeExpired, DuplicateInvoice, InvalidState
from apps.ledger.models import LedgerEntry, Transaction
from apps.loyalty.models import Balance, Membership
from apps.pos import codes, services
from tests import factories

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


class TestCodeLifecycle:
    def test_issue_and_resolve(self, terminal):
        code = codes.issue_code(terminal.id)

        assert codes.resolve_code(code) == str(terminal.id)
        assert codes.current_code(terminal.id) == code

    def test_reissue_invalidates_previous(self, terminal):
        """
        رمزان صالحان لنفس الطرفية في اللحظة نفسها يفتحان بابًا لخلط
        فاتورتين — الإصدار الجديد يبطل السابق فورًا.
        """
        old = codes.issue_code(terminal.id)
        new = codes.issue_code(terminal.id)

        assert codes.resolve_code(old) is None
        assert codes.resolve_code(new) == str(terminal.id)

    def test_consume_removes_both_keys(self, terminal):
        code = codes.issue_code(terminal.id)
        codes.consume_code(code)

        assert codes.resolve_code(code) is None
        assert codes.current_code(terminal.id) is None

    def test_code_is_case_insensitive(self, terminal):
        code = codes.issue_code(terminal.id)
        assert codes.resolve_code(code.lower()) == str(terminal.id)

    def test_unknown_code(self):
        assert codes.resolve_code("NOTACODE") is None
        assert codes.resolve_code("") is None

    def test_no_ambiguous_characters(self, terminal):
        code = codes.issue_code(terminal.id)
        assert not set(code) & set("O0I1")


class TestResolveTerminal:
    def test_valid_code(self, terminal):
        code = codes.issue_code(terminal.id)
        assert services.resolve_terminal(code).id == terminal.id

    def test_expired_code_raises(self):
        with pytest.raises(CodeExpired):
            services.resolve_terminal("EXPIRED9")

    def test_inactive_terminal_raises(self, terminal):
        code = codes.issue_code(terminal.id)
        terminal.is_active = False
        terminal.save(update_fields=["is_active"])

        with pytest.raises(CodeExpired):
            services.resolve_terminal(code)


class TestCreateTransaction:
    def test_creates_pending_without_granting(self, terminal, customer, program):
        code = codes.issue_code(terminal.id)

        txn = services.create_transaction(
            code=code,
            customer=customer,
            invoice_amount=Decimal("100"),
            invoice_no="A-1",
        )

        assert txn.status == Transaction.STATUS_PENDING
        # لا قيد ولا رصيد قبل التأكيد
        assert LedgerEntry.objects.count() == 0
        assert Balance.objects.count() == 0

    def test_code_consumed_immediately(self, terminal, customer):
        """
        الرمز يُستهلك لحظة الإنشاء لا لحظة التأكيد: بين الخطوتين قد
        تمر دقائق يستطيع فيها عميل آخر المسح على نفس الفاتورة.
        """
        code = codes.issue_code(terminal.id)

        services.create_transaction(
            code=code, customer=customer, invoice_amount=Decimal("50"), invoice_no="A-2"
        )

        assert codes.resolve_code(code) is None

    def test_duplicate_invoice_rejected(self, terminal, customer):
        code = codes.issue_code(terminal.id)
        services.create_transaction(
            code=code, customer=customer, invoice_amount=Decimal("50"), invoice_no="DUP"
        )

        code2 = codes.issue_code(terminal.id)
        with pytest.raises(DuplicateInvoice):
            services.create_transaction(
                code=code2,
                customer=customer,
                invoice_amount=Decimal("50"),
                invoice_no="DUP",
            )


class TestConfirmTransaction:
    def test_full_cycle_grants_points(self, terminal, cashier, customer, program):
        code = codes.issue_code(terminal.id)
        txn = services.create_transaction(
            code=code,
            customer=customer,
            invoice_amount=Decimal("250"),
            invoice_no="C-1",
        )

        entries = services.confirm_transaction(txn.id, staff_user=cashier)

        assert len(entries) == 1
        txn.refresh_from_db()
        assert txn.status == Transaction.STATUS_CONFIRMED
        assert txn.staff_user_id == cashier.id
        assert txn.confirmed_at is not None

        balance = Balance.objects.get(program=program)
        assert balance.amount == Decimal("250")

    def test_membership_created_on_first_purchase(
        self, terminal, cashier, customer, program, brand
    ):
        code = codes.issue_code(terminal.id)
        txn = services.create_transaction(
            code=code, customer=customer, invoice_amount=Decimal("80"), invoice_no="C-2"
        )

        services.confirm_transaction(txn.id, staff_user=cashier)

        assert Membership.objects.filter(customer=customer, brand=brand).exists()

    def test_welcome_bonus_on_first_purchase(self, terminal, cashier, customer, program):
        rule = program.rule
        rule.welcome_bonus = 50
        rule.save(update_fields=["welcome_bonus"])

        code = codes.issue_code(terminal.id)
        txn = services.create_transaction(
            code=code, customer=customer, invoice_amount=Decimal("100"), invoice_no="C-3"
        )

        services.confirm_transaction(txn.id, staff_user=cashier)

        # ٥٠ ترحيب + ١٠٠ منح
        assert Balance.objects.get(program=program).amount == Decimal("150")

    def test_second_confirm_rejected(self, terminal, cashier, customer, program):
        code = codes.issue_code(terminal.id)
        txn = services.create_transaction(
            code=code, customer=customer, invoice_amount=Decimal("100"), invoice_no="C-4"
        )
        services.confirm_transaction(txn.id, staff_user=cashier)

        with pytest.raises(InvalidState):
            services.confirm_transaction(txn.id, staff_user=cashier)

        assert LedgerEntry.objects.filter(transaction=txn).count() == 1

    def test_cashier_from_other_branch_rejected(self, terminal, customer, program):
        """كاشير فرع آخر لا يؤكّد عمليات ليست له."""
        foreign_cashier = factories.StaffUserFactory()

        code = codes.issue_code(terminal.id)
        txn = services.create_transaction(
            code=code, customer=customer, invoice_amount=Decimal("100"), invoice_no="C-5"
        )

        with pytest.raises(PermissionDenied):
            services.confirm_transaction(txn.id, staff_user=foreign_cashier)

    def test_below_minimum_confirms_without_entry(self, terminal, cashier, customer, program):
        """فاتورة دون الحد الأدنى: العملية تُؤكَّد ولا يُكتب قيد."""
        rule = program.rule
        rule.min_invoice = Decimal("100")
        rule.save(update_fields=["min_invoice"])

        code = codes.issue_code(terminal.id)
        txn = services.create_transaction(
            code=code, customer=customer, invoice_amount=Decimal("40"), invoice_no="C-6"
        )

        entries = services.confirm_transaction(txn.id, staff_user=cashier)

        assert entries == []
        txn.refresh_from_db()
        assert txn.status == Transaction.STATUS_CONFIRMED

    def test_multiple_programs_all_granted(self, terminal, cashier, customer, brand):
        """علامة تُشغّل نقاطًا وأختامًا معًا: كلاهما يُمنح من فاتورة واحدة."""
        from apps.loyalty.models import LoyaltyProgram

        points = factories.LoyaltyProgramFactory(brand=brand, type=LoyaltyProgram.TYPE_POINTS)
        factories.ProgramRuleFactory(program=points, earn_rate=Decimal("1"))

        stamps = factories.LoyaltyProgramFactory(brand=brand, type=LoyaltyProgram.TYPE_STAMPS)
        factories.ProgramRuleFactory(program=stamps, earn_rate=Decimal("1"))

        code = codes.issue_code(terminal.id)
        txn = services.create_transaction(
            code=code, customer=customer, invoice_amount=Decimal("200"), invoice_no="C-7"
        )

        entries = services.confirm_transaction(txn.id, staff_user=cashier)

        assert len(entries) == 2
        assert Balance.objects.get(program=points).amount == Decimal("200")
        assert Balance.objects.get(program=stamps).amount == Decimal("1")

    def test_inactive_program_skipped(self, terminal, cashier, customer, program):
        program.is_active = False
        program.save(update_fields=["is_active"])

        code = codes.issue_code(terminal.id)
        txn = services.create_transaction(
            code=code, customer=customer, invoice_amount=Decimal("100"), invoice_no="C-8"
        )

        assert services.confirm_transaction(txn.id, staff_user=cashier) == []


class TestManualPath:
    def test_creates_customer_from_phone(self, branch, cashier, program):
        """العميل بلا تطبيق: التاجر يُدخل رقمه فيُنشأ حسابه."""
        factories.TerminalFactory(branch=branch)

        txn = services.create_manual_transaction(
            staff_user=cashier,
            phone="01055667788",
            invoice_amount=Decimal("150"),
            invoice_no="M-1",
        )

        assert txn.customer.phone == "+201055667788"
        assert txn.staff_user_id == cashier.id

    def test_manual_then_confirm_grants(self, branch, cashier, program):
        factories.TerminalFactory(branch=branch)

        txn = services.create_manual_transaction(
            staff_user=cashier,
            phone="01055667788",
            invoice_amount=Decimal("150"),
            invoice_no="M-2",
        )
        services.confirm_transaction(txn.id, staff_user=cashier)

        assert Balance.objects.get(program=program).amount == Decimal("150")

    def test_no_terminal_rejected(self, cashier):
        with pytest.raises(InvalidState):
            services.create_manual_transaction(
                staff_user=cashier,
                phone="01055667788",
                invoice_amount=Decimal("10"),
                invoice_no="M-3",
            )


class TestFraudSignals:
    def test_self_transaction_flagged_high(self, terminal, branch, program):
        """الكاشير يمنح نقاطًا لرقمه: أخطر نمط احتيال داخلي."""
        from apps.fraud.models import FraudSignal

        cashier = factories.StaffUserFactory(branch=branch)
        customer = factories.CustomerFactory(phone=cashier.user.phone)

        code = codes.issue_code(terminal.id)
        txn = services.create_transaction(
            code=code, customer=customer, invoice_amount=Decimal("100"), invoice_no="F-1"
        )
        services.confirm_transaction(txn.id, staff_user=cashier)

        signal = FraudSignal.objects.get(transaction=txn, rule_code="staff_self_transaction")
        assert signal.severity == FraudSignal.SEVERITY_HIGH

    def test_round_amount_flagged_low(self, terminal, cashier, customer, program):
        from apps.fraud.models import FraudSignal

        code = codes.issue_code(terminal.id)
        txn = services.create_transaction(
            code=code, customer=customer, invoice_amount=Decimal("1000"), invoice_no="F-2"
        )
        services.confirm_transaction(txn.id, staff_user=cashier)

        assert FraudSignal.objects.filter(transaction=txn, rule_code="round_amount").exists()

    def test_normal_transaction_not_flagged(self, terminal, cashier, customer, program):
        from apps.fraud.models import FraudSignal

        code = codes.issue_code(terminal.id)
        txn = services.create_transaction(
            code=code, customer=customer, invoice_amount=Decimal("137.50"), invoice_no="F-3"
        )
        services.confirm_transaction(txn.id, staff_user=cashier)

        assert not FraudSignal.objects.filter(transaction=txn).exists()

    def test_signal_does_not_block_grant(self, terminal, branch, program):
        """الإشارة ترفع راية ولا تمنع النقاط — القرار للمالك."""
        cashier = factories.StaffUserFactory(branch=branch)
        customer = factories.CustomerFactory(phone=cashier.user.phone)

        code = codes.issue_code(terminal.id)
        txn = services.create_transaction(
            code=code, customer=customer, invoice_amount=Decimal("100"), invoice_no="F-4"
        )
        services.confirm_transaction(txn.id, staff_user=cashier)

        assert Balance.objects.get(program=program).amount == Decimal("100")
