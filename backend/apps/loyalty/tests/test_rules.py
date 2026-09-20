"""
حساب المنح لكل نموذج ولاء.

دوال خالصة، فالاختبارات هنا سريعة ولا تلمس قاعدة البيانات إلا
لإنشاء القاعدة نفسها.
"""

from decimal import Decimal

import pytest

from apps.loyalty.models import LoyaltyProgram
from apps.loyalty.rules import compute_delta, compute_expiry
from tests import factories

pytestmark = pytest.mark.django_db


def _rule(program_type, **kwargs):
    program = factories.LoyaltyProgramFactory(type=program_type)
    return factories.ProgramRuleFactory(program=program, **kwargs)


class TestPoints:
    def test_one_point_per_pound(self):
        rule = _rule(LoyaltyProgram.TYPE_POINTS, earn_rate=Decimal("1"))
        assert compute_delta(rule, Decimal("250")) == Decimal("250")

    def test_fractional_rate(self):
        rule = _rule(LoyaltyProgram.TYPE_POINTS, earn_rate=Decimal("0.5"))
        assert compute_delta(rule, Decimal("101")) == Decimal("50")

    def test_rounds_down_never_up(self):
        """العميل لا يربح كسرًا لم يدفع مقابله."""
        rule = _rule(LoyaltyProgram.TYPE_POINTS, earn_rate=Decimal("0.3"))
        assert compute_delta(rule, Decimal("99")) == Decimal("29")

    def test_below_minimum_grants_nothing(self):
        rule = _rule(LoyaltyProgram.TYPE_POINTS, min_invoice=Decimal("50"))
        assert compute_delta(rule, Decimal("49.99")) == Decimal("0")

    def test_exactly_minimum_grants(self):
        rule = _rule(LoyaltyProgram.TYPE_POINTS, min_invoice=Decimal("50"))
        assert compute_delta(rule, Decimal("50")) == Decimal("50")


class TestStampsAndVisits:
    @pytest.mark.parametrize(
        "program_type", [LoyaltyProgram.TYPE_STAMPS, LoyaltyProgram.TYPE_VISITS]
    )
    def test_one_per_invoice_regardless_of_amount(self, program_type):
        rule = _rule(program_type, earn_rate=Decimal("1"))

        assert compute_delta(rule, Decimal("10")) == Decimal("1")
        assert compute_delta(rule, Decimal("10000")) == Decimal("1")

    def test_minimum_invoice_blocks_splitting(self):
        """
        تفتيت الفاتورة للحصول على أختام مجانية: الحد الأدنى يغلقه.
        """
        rule = _rule(LoyaltyProgram.TYPE_STAMPS, min_invoice=Decimal("100"))

        assert compute_delta(rule, Decimal("30")) == Decimal("0")
        assert compute_delta(rule, Decimal("120")) == Decimal("1")


class TestCashback:
    def test_percentage_of_invoice(self):
        rule = _rule(LoyaltyProgram.TYPE_CASHBACK, earn_rate=Decimal("5"))
        assert compute_delta(rule, Decimal("200")) == Decimal("10.00")

    def test_rounds_to_piastres(self):
        rule = _rule(LoyaltyProgram.TYPE_CASHBACK, earn_rate=Decimal("3"))
        assert compute_delta(rule, Decimal("33.33")) == Decimal("1.00")


class TestGifts:
    def test_never_automatic(self):
        """الهدايا بقرار من التاجر لا تلقائيًا بالفاتورة."""
        rule = _rule(LoyaltyProgram.TYPE_GIFTS, earn_rate=Decimal("1"))
        assert compute_delta(rule, Decimal("500")) == Decimal("0")


class TestEdgeCases:
    def test_zero_invoice(self):
        rule = _rule(LoyaltyProgram.TYPE_POINTS)
        assert compute_delta(rule, Decimal("0")) == Decimal("0")

    def test_negative_invoice(self):
        rule = _rule(LoyaltyProgram.TYPE_POINTS)
        assert compute_delta(rule, Decimal("-100")) == Decimal("0")

    def test_none_invoice(self):
        rule = _rule(LoyaltyProgram.TYPE_POINTS)
        assert compute_delta(rule, None) == Decimal("0")


class TestExpiry:
    def test_months_added(self):
        from django.utils import timezone

        rule = _rule(LoyaltyProgram.TYPE_POINTS, expiry_months=6)
        expiry = compute_expiry(rule)

        assert expiry is not None
        assert expiry > timezone.now()

    def test_zero_months_means_never(self):
        rule = _rule(LoyaltyProgram.TYPE_POINTS, expiry_months=0)
        assert compute_expiry(rule) is None

    def test_none_falls_back_to_setting(self):
        rule = _rule(LoyaltyProgram.TYPE_POINTS, expiry_months=None)
        assert compute_expiry(rule) is not None

    def test_month_end_clamped(self, monkeypatch):
        """
        ٣١ يناير + شهر واحد = ٢٨ فبراير لا خطأ.

        هذا العطل يظهر مرة واحدة في السنة ويوقف كل منح في ذلك اليوم.
        """
        from datetime import datetime

        from django.utils import timezone as tz

        fixed = tz.make_aware(datetime(2026, 1, 31, 12, 0))
        monkeypatch.setattr(tz, "now", lambda: fixed)

        rule = _rule(LoyaltyProgram.TYPE_POINTS, expiry_months=1)
        expiry = compute_expiry(rule)

        assert (expiry.year, expiry.month, expiry.day) == (2026, 2, 28)


class TestUnitLabels:
    @pytest.mark.parametrize(
        "program_type,expected",
        [
            (LoyaltyProgram.TYPE_POINTS, "نقطة"),
            (LoyaltyProgram.TYPE_STAMPS, "ختم"),
            (LoyaltyProgram.TYPE_VISITS, "زيارة"),
            (LoyaltyProgram.TYPE_CASHBACK, "جنيه"),
            (LoyaltyProgram.TYPE_GIFTS, "هدية"),
        ],
    )
    def test_label_matches_type(self, program_type, expected):
        program = factories.LoyaltyProgramFactory(type=program_type)
        assert program.unit_label == expected
