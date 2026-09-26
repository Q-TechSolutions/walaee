"""
التوصيات الإحصائية — والخطر أن تبدو صحيحة وهي على لا شيء.

توصية مبنيّة على سبع فواتير تُعرَض في الشاشة بنفس خطّ توصية مبنيّة
على سبعة آلاف. والتاجر يسعّر مكافأته عليها، فيكتشف الخطأ في
التزامه القائم بعد شهر — لا في الشاشة التي أعطته الرقم.

لذلك أول ما يُثبَّت هنا ليس دقّة الحساب بل **الامتناع**: أن
`enough_data` تكون كاذبة تحت العتبة، وأن قائمة البرامج تعود
فارغة، وألا يُعاد رقم يُبنى عليه قرار. ثم تُثبَّت الترجمة إلى
وحدة كل نموذج، لأن «٦ أختام» لبرنامج نقاط رقمٌ صحيح حسابيًا
وبلا معنى.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.ledger.insights import (
    MIN_INVOICES,
    MIN_VISITS,
    best_send_time,
    suggested_reward_value,
)
from apps.ledger.models import Transaction
from apps.loyalty.models import LoyaltyProgram
from tests import factories

pytestmark = pytest.mark.django_db


def invoice(terminal, customer, amount: str, *, moment=None, index: int = 0) -> Transaction:
    moment = moment or timezone.now()
    return Transaction.objects.create(
        terminal=terminal,
        customer=customer,
        invoice_no=f"I{index}-{moment.timestamp():.0f}",
        invoice_amount=Decimal(amount),
        status=Transaction.STATUS_CONFIRMED,
        confirmed_at=moment,
        created_at=moment,
    )


def fill(terminal, customer, count: int, amount: str = "100", *, moment=None):
    for index in range(count):
        invoice(terminal, customer, amount, moment=moment, index=index)


class TestItRefusesToGuess:
    def test_reward_value_says_so_when_the_sample_is_thin(self, brand, terminal, customer, program):
        fill(terminal, customer, MIN_INVOICES - 1)

        result = suggested_reward_value(brand)

        assert result["enough_data"] is False
        assert result["sample"] == MIN_INVOICES - 1
        assert result["needed"] == MIN_INVOICES
        assert result["programs"] == []

    def test_reward_value_on_an_empty_brand_does_not_divide_by_zero(self, brand, program):
        result = suggested_reward_value(brand)

        assert result["enough_data"] is False
        assert result["sample"] == 0
        assert result["average_invoice"] == "0.00"

    def test_send_time_says_so_when_the_sample_is_thin(self, brand, terminal, customer):
        fill(terminal, customer, MIN_VISITS - 1)

        result = best_send_time(brand)

        assert result["enough_data"] is False
        assert result["days"] == []
        assert result["hours"] == []

    def test_pending_transactions_do_not_count(self, brand, terminal, customer, program):
        """
        العملية غير المؤكَّدة لم تحدث بعد.

        عدّها يرفع حجم العيّنة فوق العتبة بفواتير قد يرفضها التاجر
        — فتُبنى التوصية على مبيعات لم تتم.
        """
        for index in range(MIN_INVOICES + 20):
            Transaction.objects.create(
                terminal=terminal,
                customer=customer,
                invoice_no=f"P{index}",
                invoice_amount=Decimal("100"),
                status=Transaction.STATUS_PENDING,
            )

        assert suggested_reward_value(brand)["enough_data"] is False

    def test_transactions_outside_the_window_do_not_count(self, brand, terminal, customer, program):
        """نافذة تسعين يومًا: مبيعات العام الماضي لا تسعّر مكافأة اليوم."""
        old = timezone.now() - timedelta(days=200)
        fill(terminal, customer, MIN_INVOICES + 10, moment=old)

        assert suggested_reward_value(brand, days=90)["enough_data"] is False


class TestRewardValue:
    def test_it_scales_with_the_average_invoice(self, brand, terminal, customer, program):
        """
        متجر متوسط فاتورته ضعف متجر آخر تكون مكافأته أغلى.

        هذا هو كل ما تعنيه التوصية: المكافأة تُقاس بما ينفقه عميل
        هذا المتجر، لا برقم عام.
        """
        fill(terminal, customer, MIN_INVOICES, "200")

        result = suggested_reward_value(brand)

        assert result["enough_data"] is True
        assert result["average_invoice"] == "200.00"
        assert Decimal(result["programs"][0]["reward_worth"]) > 0

    def test_the_range_brackets_the_suggestion(self, brand, terminal, customer, program):
        """
        الحدّان ليسا زينة: التاجر يحتاج مدى يتحرّك فيه لا رقمًا
        واحدًا يأخذه أو يتركه.
        """
        fill(terminal, customer, MIN_INVOICES, "150")

        row = suggested_reward_value(brand)["programs"][0]

        assert Decimal(row["cost_low"]) <= Decimal(row["cost_amount"])
        assert Decimal(row["cost_amount"]) <= Decimal(row["cost_high"])

    def test_a_stamps_programme_is_priced_in_stamps(self, brand, terminal, customer):
        """
        «٤٢٠ ختمًا» رقم صحيح حسابيًا وبلا معنى.

        الوحدة تختلف بالنموذج، فالترجمة تختلف معها: الختم يُكتسب
        بالزيارة لا بالجنيه.
        """
        stamps = factories.LoyaltyProgramFactory(brand=brand, type=LoyaltyProgram.TYPE_STAMPS)
        factories.ProgramRuleFactory(program=stamps)
        fill(terminal, customer, MIN_INVOICES, "200")

        row = next(
            r
            for r in suggested_reward_value(brand)["programs"]
            if r["program_id"] == str(stamps.id)
        )

        assert Decimal(row["cost_amount"]) <= 20

    def test_a_cashback_programme_is_priced_in_pounds(self, brand, terminal, customer):
        cashback = factories.LoyaltyProgramFactory(brand=brand, type=LoyaltyProgram.TYPE_CASHBACK)
        factories.ProgramRuleFactory(program=cashback)
        fill(terminal, customer, MIN_INVOICES, "100")

        row = next(
            r
            for r in suggested_reward_value(brand)["programs"]
            if r["program_id"] == str(cashback.id)
        )

        assert Decimal(row["cost_amount"]) == Decimal(row["reward_worth"])

    def test_a_programme_without_a_rule_is_skipped(self, brand, terminal, customer, program):
        """برنامج بلا قاعدة لا يمنح شيئًا — واقتراح تكلفة مكافأته بلا معنى."""
        factories.LoyaltyProgramFactory(brand=brand, name="بلا قاعدة")
        fill(terminal, customer, MIN_INVOICES, "100")

        names = [r["program_name"] for r in suggested_reward_value(brand)["programs"]]

        assert "بلا قاعدة" not in names

    def test_another_brand_does_not_move_the_number(self, brand, terminal, customer, program):
        """توصية هذه العلامة من فواتير هذه العلامة وحدها."""
        stranger = factories.TerminalFactory()
        fill(stranger, customer, 500, "9000")
        fill(terminal, customer, MIN_INVOICES, "100")

        assert suggested_reward_value(brand)["average_invoice"] == "100.00"


class TestSendTime:
    def test_it_finds_the_busiest_weekday(self, brand, terminal, customer):
        """
        الحملة تصل حين يكون العميل على وشك السلوك الذي نريده.

        أكثر يوم يشتري فيه عملاء هذا المتجر هو أقرب نافذة إليه.
        """
        # كل الزيارات في يوم واحد معروف
        base = timezone.localtime(timezone.now()).replace(
            hour=14, minute=0, second=0, microsecond=0
        )
        while base.weekday() != 2:  # الأربعاء
            base -= timedelta(days=1)

        for week in range(8):
            fill(terminal, customer, 6, moment=base - timedelta(days=7 * week))

        result = best_send_time(brand)

        assert result["enough_data"] is True
        assert result["best_day"] == 2
        assert result["best_day_name"] == "الأربعاء"

    def test_it_sends_an_hour_before_the_peak(self, brand, terminal, customer):
        """
        الرسالة تحتاج وقتًا ليقرأها العميل ويقرّر.

        وصولها في ساعة الذروة نفسها يصل بعد أن قرّر أين يذهب.
        """
        base = timezone.localtime(timezone.now()).replace(
            hour=19, minute=0, second=0, microsecond=0
        )
        for day in range(10):
            fill(terminal, customer, 6, moment=base - timedelta(days=day))

        result = best_send_time(brand)

        assert result["peak_hour"] == 19
        assert result["best_hour"] == 18

    def test_midnight_peak_does_not_wrap_to_minus_one(self, brand, terminal, customer):
        """ساعة الذروة صفر تعطي ٢٣ لا ‎−١‎ — وهي ساعة لا يقبلها أي مجدول."""
        base = timezone.localtime(timezone.now()).replace(
            hour=0, minute=30, second=0, microsecond=0
        )
        for day in range(10):
            fill(terminal, customer, 6, moment=base - timedelta(days=day))

        assert best_send_time(brand)["best_hour"] == 23

    def test_it_returns_every_day_and_hour_for_the_chart(self, brand, terminal, customer):
        """
        الشاشة ترسم توزيعًا لا رقمًا.

        التاجر يصدّق التوصية حين يرى الأعمدة التي بُنيت عليها —
        وقائمة ناقصة تكسر الرسم في أيام بلا زيارات.
        """
        fill(terminal, customer, MIN_VISITS + 5)

        result = best_send_time(brand)

        assert len(result["days"]) == 7
        assert len(result["hours"]) == 24
        assert sum(d["visits"] for d in result["days"]) == result["sample"]


class TestConfidence:
    def test_a_bare_sample_is_low(self, brand, terminal, customer, program):
        fill(terminal, customer, MIN_INVOICES)

        assert suggested_reward_value(brand)["confidence"] == "low"

    def test_a_deep_sample_is_high(self, brand, terminal, customer, program):
        fill(terminal, customer, MIN_INVOICES * 5)

        assert suggested_reward_value(brand)["confidence"] == "high"
