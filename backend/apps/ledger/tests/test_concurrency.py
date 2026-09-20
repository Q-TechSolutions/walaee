"""
اختبارات التزامن — الاختبار الذي لا يُتنازل عنه.

خطأ واحد في الرصيد يساوي فقدان ثقة التاجر نهائيًا، وهي خسارة لا
تُسترد بإصلاح لاحق. هذه الاختبارات تشغّل خيوطًا متوازية على اتصالات
قاعدة بيانات منفصلة لتحاكي ما يحدث فعليًا عند الصندوق.

ملاحظة تقنية: كل خيط يفتح اتصاله الخاص، ولذلك يجب إغلاقه صراحةً
في النهاية وإلا بقيت الاتصالات معلّقة ومنعت pytest من إسقاط قاعدة
بيانات الاختبار.

المرجع: docs/architecture/testing.md
"""

from decimal import Decimal
from threading import Barrier, BrokenBarrierError, Thread

import pytest
from django.db import connections, transaction

from apps.ledger.models import LedgerEntry, Transaction
from apps.ledger.services import LedgerError, apply_entry
from apps.loyalty.models import Balance
from apps.pos.services import confirm_transaction
from tests import factories

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.concurrency]


def _run_parallel(target, count: int):
    """
    يشغّل `target` في عدة خيوط تبدأ في اللحظة نفسها.

    الحاجز يضمن تزامنًا حقيقيًا: بلا حاجز قد ينتهي الخيط الأول قبل
    أن يبدأ الثاني، فيمرّ الاختبار بلا أن يختبر التزامن أصلًا.
    """
    barrier = Barrier(count, timeout=10)
    errors: list[Exception] = []

    def wrapper():
        try:
            barrier.wait()
            target()
        except BrokenBarrierError:  # pragma: no cover
            errors.append(RuntimeError("barrier broken"))
        except Exception as exc:
            errors.append(exc)
        finally:
            # إغلاق اتصال هذا الخيط — إهماله يعلّق تفكيك قاعدة الاختبار
            connections.close_all()

    threads = [Thread(target=wrapper) for _ in range(count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    return errors


class TestDoubleConfirm:
    def test_double_confirm_grants_points_once(self, terminal, cashier, customer, program):
        """ضغطتان متزامنتان على «تأكيد» = منح واحد فقط."""
        txn = Transaction.objects.create(
            terminal=terminal,
            customer=customer,
            invoice_no="INV-001",
            invoice_amount=Decimal("100"),
            status=Transaction.STATUS_PENDING,
        )

        errors = _run_parallel(lambda: confirm_transaction(txn.id, staff_user=cashier), count=2)

        entries = LedgerEntry.objects.filter(transaction=txn)
        assert entries.count() == 1, f"منحت النقاط أكثر من مرة · errors={[repr(e) for e in errors]}"
        assert len(errors) == 1, "الضغطة الثانية كان يجب أن تُرفض"

        txn.refresh_from_db()
        assert txn.status == Transaction.STATUS_CONFIRMED

        balance = Balance.objects.get(program=program)
        assert balance.amount == Decimal("100")

    def test_three_simultaneous_confirms(self, terminal, cashier, customer, program):
        """ثلاث ضغطات: واحدة تنجح واثنتان تُرفضان."""
        txn = Transaction.objects.create(
            terminal=terminal,
            customer=customer,
            invoice_no="INV-002",
            invoice_amount=Decimal("250"),
            status=Transaction.STATUS_PENDING,
        )

        errors = _run_parallel(lambda: confirm_transaction(txn.id, staff_user=cashier), count=3)

        assert LedgerEntry.objects.filter(transaction=txn).count() == 1
        assert len(errors) == 2
        assert Balance.objects.get(program=program).amount == Decimal("250")


class TestParallelEarning:
    def test_parallel_entries_all_counted(self, membership, program):
        """
        خمس حركات متوازية على نفس المحفظة: كلها تُكتب والرصيد صحيح.

        هذا عكس الاختبار السابق: هنا كل حركة مشروعة، والمطلوب ألا
        يضيع أي منها بسبب تحديث فوق آخر (lost update).
        """

        def earn():
            apply_entry(
                membership=membership,
                program=program,
                delta=Decimal("10"),
                reason=LedgerEntry.REASON_EARN,
            )

        errors = _run_parallel(earn, count=5)

        assert errors == []
        assert LedgerEntry.objects.filter(membership=membership).count() == 5
        assert Balance.objects.get(membership=membership).amount == Decimal("50")

    def test_parallel_redemptions_cannot_overdraw(self, membership, program):
        """
        رصيد ١٠٠ وثلاث محاولات خصم ٨٠ في اللحظة نفسها.

        واحدة فقط يجب أن تنجح. بلا قفل كانت الثلاث ستقرأ ١٠٠ وتمرّ،
        فينتهي الرصيد إلى ‎-١٤٠.
        """
        apply_entry(
            membership=membership,
            program=program,
            delta=Decimal("100"),
            reason=LedgerEntry.REASON_EARN,
        )

        def redeem():
            apply_entry(
                membership=membership,
                program=program,
                delta=Decimal("-80"),
                reason=LedgerEntry.REASON_REDEEM,
            )

        errors = _run_parallel(redeem, count=3)

        balance = Balance.objects.get(membership=membership, program=program)
        assert balance.amount == Decimal("20")
        assert len(errors) == 2
        assert all(isinstance(e, LedgerError) for e in errors)


class TestDuplicateInvoice:
    def test_same_invoice_twice_rejected(self, terminal, customer):
        """
        القيد الفريد على (terminal, invoice_no) يمنع تسجيل الفاتورة مرتين.
        """
        from django.db import IntegrityError

        Transaction.objects.create(
            terminal=terminal,
            customer=customer,
            invoice_no="INV-DUP",
            invoice_amount=Decimal("50"),
        )

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Transaction.objects.create(
                    terminal=terminal,
                    customer=customer,
                    invoice_no="INV-DUP",
                    invoice_amount=Decimal("50"),
                )

    def test_same_invoice_different_terminal_allowed(self, branch, customer):
        """طرفيتان مختلفتان قد تصدران نفس رقم الفاتورة بشكل مشروع."""
        t1 = factories.TerminalFactory(branch=branch)
        t2 = factories.TerminalFactory(branch=branch)

        Transaction.objects.create(
            terminal=t1, customer=customer, invoice_no="A-1", invoice_amount=Decimal("10")
        )
        Transaction.objects.create(
            terminal=t2, customer=customer, invoice_no="A-1", invoice_amount=Decimal("10")
        )

        assert Transaction.objects.count() == 2
