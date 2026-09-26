"""
ما تحتاجه محفظة العميل لترسم نفسها: الهدف التالي وسلسلة الزيارات.

كلاهما أُضيف ليُملأ تصميمٌ معتمد ببيانات **حقيقية**. الإغراء هنا
أن تُلفَّق الأرقام لتبدو الشاشة مليئة في العرض — وهذه الاختبارات
تثبت أنها محسوبة من دفتر القيود والعمليات لا من الهواء.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.services import issue_tokens_for_customer
from apps.ledger.models import Transaction
from apps.ledger.services import apply_entry
from apps.pos import codes
from tests import factories

pytestmark = pytest.mark.django_db


@pytest.fixture
def me(customer):
    client = APIClient()
    tokens = issue_tokens_for_customer(customer)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


@pytest.fixture
def card(customer, brand, program):
    """عضوية برصيد ١٢٠ وبرنامج فيه مكافأتان."""
    membership = factories.MembershipFactory(customer=customer, brand=brand)
    apply_entry(
        membership=membership,
        program=program,
        delta=Decimal("120"),
        reason="earn",
        actor=None,
    )
    factories.RewardFactory(program=program, title="مكافأة غالية", cost_amount=Decimal("500"))
    factories.RewardFactory(program=program, title="مكافأة قريبة", cost_amount=Decimal("200"))
    return membership


class TestNextReward:
    def test_target_is_the_cheapest_one_not_yet_affordable(self, me, card):
        """
        الهدف أمام العميل لا خلفه. رصيده ١٢٠، والمكافأتان ٢٠٠ و٥٠٠،
        فهدفه ٢٠٠.
        """
        body = me.get(reverse("me:cards")).json()

        assert body[0]["next_reward"]["title"] == "مكافأة قريبة"

    def test_an_affordable_reward_is_skipped(self, me, customer, brand, program):
        """
        العطل الذي كشفته الشاشة: رصيد ٣٤٠ وأرخص مكافأة بـ١٠٠ كان
        يعطي «٣٤٠ من ١٠٠» فوق شريط ممتلئ — هدف تجاوزه من زمن.
        """
        membership = factories.MembershipFactory(customer=customer, brand=brand)
        apply_entry(
            membership=membership,
            program=program,
            delta=Decimal("340"),
            reason="earn",
            actor=None,
        )
        factories.RewardFactory(program=program, title="رخيصة", cost_amount=Decimal("100"))
        factories.RewardFactory(program=program, title="التالية", cost_amount=Decimal("500"))

        target = me.get(reverse("me:cards")).json()[0]["next_reward"]

        assert target["title"] == "التالية"
        assert target["remaining"] == "160.00"
        assert target["reached"] is False

    def test_all_affordable_means_reached(self, me, customer, brand, program):
        """من يستطيع صرف كل شيء لا هدف أمامه — الشريط يقول «تمّ»."""
        membership = factories.MembershipFactory(customer=customer, brand=brand)
        apply_entry(
            membership=membership,
            program=program,
            delta=Decimal("900"),
            reason="earn",
            actor=None,
        )
        factories.RewardFactory(program=program, title="أ", cost_amount=Decimal("100"))
        factories.RewardFactory(program=program, title="ب", cost_amount=Decimal("300"))

        target = me.get(reverse("me:cards")).json()[0]["next_reward"]

        assert target["reached"] is True
        assert target["progress"] == 1.0
        assert target["remaining"] == "0"

    def test_progress_is_balance_over_cost(self, me, card):
        body = me.get(reverse("me:cards")).json()

        # ١٢٠ من ٢٠٠
        assert body[0]["next_reward"]["progress"] == pytest.approx(0.6)

    def test_remaining_is_what_is_left(self, me, card):
        body = me.get(reverse("me:cards")).json()

        assert body[0]["next_reward"]["remaining"] == "80.00"

    def test_progress_never_exceeds_one(self, me, customer, brand, program):
        """النسبة تُمرَّر إلى عرض CSS — تجاوزها الواحد يمدّ الشريط خارج إطاره."""
        membership = factories.MembershipFactory(customer=customer, brand=brand)
        apply_entry(
            membership=membership,
            program=program,
            delta=Decimal("900"),
            reason="earn",
            actor=None,
        )
        factories.RewardFactory(program=program, cost_amount=Decimal("100"))

        body = me.get(reverse("me:cards")).json()

        assert body[0]["next_reward"]["progress"] == 1.0

    def test_no_reward_means_no_target(self, me, customer, brand, program):
        """برنامج بلا مكافآت لا يرسم شريط تقدّم نحو لا شيء."""
        membership = factories.MembershipFactory(customer=customer, brand=brand)
        apply_entry(
            membership=membership, program=program, delta=Decimal("50"), reason="earn", actor=None
        )

        body = me.get(reverse("me:cards")).json()

        assert body[0]["next_reward"] is None
        assert body[0]["balances"][0]["next_reward"] is None

    def test_inactive_reward_is_not_a_target(self, me, card):
        from apps.loyalty.models import Reward

        Reward.objects.filter(title="مكافأة قريبة").update(is_active=False)

        body = me.get(reverse("me:cards")).json()

        assert body[0]["next_reward"]["title"] == "مكافأة غالية"

    def test_wallet_of_many_brands_stays_one_query_for_rewards(self, me, customer, program):
        """
        الاستعلام الموحّد ليس ترفًا: الشاشة تُفتح عند كل تشغيل
        للتطبيق، واستعلام لكل بطاقة يعني عشرة استعلامات لعميل في
        عشر علامات.
        """
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        for _ in range(5):
            brand = factories.BrandFactory()
            other = factories.LoyaltyProgramFactory(brand=brand)
            factories.ProgramRuleFactory(program=other)
            membership = factories.MembershipFactory(customer=customer, brand=brand)
            apply_entry(
                membership=membership,
                program=other,
                delta=Decimal("10"),
                reason="earn",
                actor=None,
            )
            factories.RewardFactory(program=other, cost_amount=Decimal("100"))

        with CaptureQueriesContext(connection) as captured:
            me.get(reverse("me:cards"))

        reward_queries = [q for q in captured.captured_queries if "loyalty_reward" in q["sql"]]
        assert len(reward_queries) == 1


class TestWeekStreak:
    def test_seven_days_always(self, me):
        body = me.get(reverse("me:summary")).json()

        assert len(body["week"]) == 7

    def test_last_day_is_today(self, me):
        body = me.get(reverse("me:summary")).json()

        assert body["week"][-1]["today"] is True
        assert body["week"][-1]["date"] == timezone.localdate().isoformat()
        assert sum(1 for day in body["week"] if day["today"]) == 1

    def test_no_visits_means_all_off(self, me):
        body = me.get(reverse("me:summary")).json()

        assert all(day["visited"] is False for day in body["week"])

    def test_a_confirmed_purchase_lights_its_day(self, me, customer, terminal, cashier, program):
        code = codes.issue_code(terminal.id)
        from apps.pos import services as pos

        txn = pos.create_transaction(
            code=code,
            customer=customer,
            invoice_amount=Decimal("100"),
            invoice_no="W-1",
        )
        pos.confirm_transaction(txn.id, staff_user=cashier)

        body = me.get(reverse("me:summary")).json()

        assert body["week"][-1]["visited"] is True

    def test_pending_transaction_is_not_a_visit(self, me, customer, terminal, program):
        """
        عملية لم يؤكّدها الكاشير ليست زيارة: احتسابها يعني شريطًا
        يضيء لمن دخل المتجر وخرج بلا شراء.
        """
        from apps.pos import services as pos

        pos.create_transaction(
            code=codes.issue_code(terminal.id),
            customer=customer,
            invoice_amount=Decimal("100"),
            invoice_no="W-2",
        )

        body = me.get(reverse("me:summary")).json()

        assert all(day["visited"] is False for day in body["week"])

    def test_old_visits_fall_out_of_the_window(self, me, customer, terminal, cashier, program):
        from apps.pos import services as pos

        txn = pos.create_transaction(
            code=codes.issue_code(terminal.id),
            customer=customer,
            invoice_amount=Decimal("100"),
            invoice_no="W-3",
        )
        pos.confirm_transaction(txn.id, staff_user=cashier)
        Transaction.objects.filter(pk=txn.pk).update(created_at=timezone.now() - timedelta(days=9))

        body = me.get(reverse("me:summary")).json()

        assert all(day["visited"] is False for day in body["week"])

    def test_another_customer_does_not_light_my_streak(self, me, terminal, cashier, program):
        from apps.pos import services as pos

        stranger = factories.CustomerFactory()
        txn = pos.create_transaction(
            code=codes.issue_code(terminal.id),
            customer=stranger,
            invoice_amount=Decimal("100"),
            invoice_no="W-4",
        )
        pos.confirm_transaction(txn.id, staff_user=cashier)

        body = me.get(reverse("me:summary")).json()

        assert all(day["visited"] is False for day in body["week"])

    def test_every_day_carries_a_letter(self, me):
        body = me.get(reverse("me:summary")).json()

        assert all(day["letter"] for day in body["week"])
