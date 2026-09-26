"""
`verify_ledger` — الأمر الذي يثبت أن الأرصدة تطابق قيودها.

هذا هو الفحص الذي يقف بين المنتج وبين أسوأ عطل ممكن فيه: رصيد
يقول رقمًا لا تقوله القيود. القيد مصدر الحقيقة، واللقطة في
`Balance` موجودة للأداء فقط — فأي اختلاف بينهما يعني مسارًا يكتب
في الرصيد خارج `apply_entry`.

الخطر أن هذا الأمر يفشل **بصمت**. يُستدعى بعد كل استرجاع نسخة
احتياطية وفي مهمة ليلية، وكلاهما يقرأ رمز الخروج لا النص. أمرٌ
يطبع «انحراف» ثم يخرج بصفر يجعل خط النشر يكمل فوق قاعدة معطوبة،
ويجعل المهمة الليلية تُسجَّل ناجحة كل ليلة بينما الأرقام تنجرف.

ولذلك يُثبَّت هنا رمز الخروج قبل النص، ويُثبَّت أن الأمر **لا
يصحّح شيئًا** ما لم يُطلَب منه صراحةً: التصحيح التلقائي يمحو
الدليل الوحيد على وجود المسار المعطوب.
"""

from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command

from apps.ledger.models import LedgerEntry
from apps.ledger.services import apply_entry
from apps.loyalty.models import Balance
from tests import factories

pytestmark = pytest.mark.django_db


def earn(membership, program, amount: str) -> None:
    apply_entry(
        membership=membership,
        program=program,
        delta=Decimal(amount),
        reason=LedgerEntry.REASON_EARN,
    )


def drift(membership, program, amount: str) -> None:
    """
    يكتب في اللقطة متجاوزًا `apply_entry`.

    `update` لا يمرّ بالخدمة ولا بأي إشارة — وهو بالضبط شكل العطل
    الذي وُجد هذا الأمر ليكشفه. لا توجد طريقة أخرى لاصطناعه:
    المحرك نفسه لا يسمح به.
    """
    Balance.objects.filter(membership=membership, program=program).update(amount=Decimal(amount))


def run(*args) -> str:
    """يشغّل الأمر ويعيد مخرجاته. يترك `SystemExit` يمرّ."""
    out = StringIO()
    call_command("verify_ledger", *args, stdout=out, stderr=out)
    return out.getvalue()


def run_failing(*args) -> tuple[int, str]:
    """
    يشغّل الأمر متوقّعًا فشله، ويعيد رمز الخروج **ومخرجاته**.

    وضع التحقّق داخل `pytest.raises` يجعله غير قابل للتنفيذ:
    السطر الذي يرمي يسبقه، فيمرّ الاختبار مهما كان المطبوع. هذه
    الدالة تلتقط الرمز والنص معًا فيبقى الاثنان قابلين للفحص.
    """
    out = StringIO()
    with pytest.raises(SystemExit) as exit_info:
        call_command("verify_ledger", *args, stdout=out, stderr=out)
    return exit_info.value.code, out.getvalue()


class TestCleanLedger:
    def test_it_reports_success_and_the_count(self, membership, program):
        earn(membership, program, "120")

        output = run()

        assert "✓" in output
        assert "1" in output

    def test_quiet_says_nothing_when_all_is_well(self, membership, program):
        """
        المهمة الليلية تعمل بـ`--quiet`.

        سطر نجاح كل ليلة يملأ السجل بضجيج يُدرَّب المشغّل على
        تجاهله — فلا يرى سطر الفشل حين يأتي.
        """
        earn(membership, program, "120")

        assert run("--quiet") == ""

    def test_a_wallet_with_no_entries_and_no_balance_is_clean(self, membership, program):
        """صفر مقابل صفر ليس انحرافًا — هذه حال كل من انضمّ للتوّ."""
        Balance.objects.create(membership=membership, program=program, amount=Decimal("0"))

        assert "✓" in run()


class TestDriftIsCaught:
    def test_a_snapshot_above_its_entries_exits_non_zero(self, membership, program):
        """
        رمز الخروج قبل النص.

        خط الاسترجاع يقرأ الرمز وحده. أمرٌ يطبع الانحراف ويخرج
        بصفر يجعل النشر يكمل فوق قاعدة معطوبة.
        """
        earn(membership, program, "100")
        drift(membership, program, "999")

        code, _ = run_failing()

        assert code == 1

    def test_it_names_the_wallet_that_drifted(self, membership, program):
        """
        من يقرأ التقرير يحتاج أن يعرف **أي** محفظة، لا عددها فقط.
        """
        earn(membership, program, "100")
        drift(membership, program, "40")

        _, output = run_failing()

        assert membership.customer.phone in output
        assert membership.brand.name in output

    def test_a_snapshot_below_its_entries_is_drift_too(self, membership, program):
        """
        الانحراف في الاتجاهين.

        فحصٌ يقارن بـ«أكبر من» فقط يمرّر رصيدًا أقلّ من قيوده —
        وهو عميل خُصم منه ما لم يُصرف.
        """
        earn(membership, program, "500")
        drift(membership, program, "10")

        code, _ = run_failing()

        assert code == 1

    def test_it_never_touches_the_snapshot_without_being_asked(self, membership, program):
        """
        التصحيح التلقائي يمحو الدليل.

        اللقطة المنحرفة هي الأثر الوحيد الباقي على المسار الذي
        كتب خارج المحرك. تصحيحها قبل فهم السبب يترك العطل يتكرر
        بلا أن يراه أحد مرة أخرى.
        """
        earn(membership, program, "100")
        drift(membership, program, "777")

        run_failing()

        balance = Balance.objects.get(membership=membership, program=program)
        assert balance.amount == Decimal("777")

    def test_one_drifted_wallet_does_not_hide_the_others(self, brand, program):
        """الأمر يفحص الكل ثم يبلّغ — لا يتوقف عند أول انحراف."""
        for _ in range(3):
            member = factories.MembershipFactory(brand=brand)
            earn(member, program, "100")
            drift(member, program, "5")

        _, output = run_failing()

        assert "انحراف في 3 من 3" in output


class TestFixSnapshots:
    def test_it_realigns_the_snapshot_to_the_entries(self, membership, program):
        """القيود مصدر الحقيقة — اللقطة هي التي تتحرّك، لا العكس."""
        earn(membership, program, "100")
        earn(membership, program, "250")
        drift(membership, program, "12")

        output = run("--fix-snapshots")

        balance = Balance.objects.get(membership=membership, program=program)
        assert balance.amount == Decimal("350")
        assert "✓" in output

    def test_it_does_not_invent_entries(self, membership, program):
        """
        التصحيح يمسّ اللقطة وحدها.

        قيدٌ تعويضي يُنشأ هنا كان سيصير جزءًا من السجل الدائم —
        سطرًا لا يقابله شيء حدث في الواقع.
        """
        earn(membership, program, "100")
        drift(membership, program, "40")
        before = LedgerEntry.objects.count()

        run("--fix-snapshots")

        assert LedgerEntry.objects.count() == before

    def test_it_exits_zero_after_fixing(self, membership, program):
        """بعد التصحيح لا شيء يمنع خط النشر من الاستمرار."""
        earn(membership, program, "100")
        drift(membership, program, "40")

        run("--fix-snapshots")  # لا SystemExit

        assert "✓" in run()

    def test_a_wallet_with_no_entries_is_zeroed(self, membership, program):
        """
        رصيد بلا قيد واحد يقابله مجموعه صفر.

        `Sum` على مجموعة فارغة تعيد `None`، ومعاملتها كصفر هي
        الفرق بين تصحيح صحيح وانهيار بـ`TypeError` في منتصف
        الاسترجاع.
        """
        Balance.objects.create(membership=membership, program=program, amount=Decimal("90"))

        run("--fix-snapshots")

        assert Balance.objects.get(membership=membership, program=program).amount == Decimal("0")


class TestLongReport:
    def test_it_caps_the_listing_and_says_how_many_it_hid(self, brand, program):
        """
        انحراف في مئة محفظة لا يُطبع مئة مرة.

        التقرير يُقرأ في طرفية أثناء حادثة؛ قائمة بلا حدّ تدفع
        السطر الأهم — عددها الكلي — خارج الشاشة.
        """
        for _ in range(52):
            member = factories.MembershipFactory(brand=brand)
            earn(member, program, "100")
            drift(member, program, "7")

        _, output = run_failing()

        assert "انحراف في 52 من 52" in output
        assert "و 2 أخرى" in output
        # الاسم يتكرّر مرة لكل محفظة مطبوعة، لا ٥٢ مرة
        assert output.count("اللقطة") == 50
