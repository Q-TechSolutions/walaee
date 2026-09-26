"""
`/me/rewards` — المكافأة ووقفة العميل منها في رد واحد.

الشاشة تفصل «جاهزة للاستبدال» عن «قريبة منك»، والفصل كله مبنيّ
على حقلَي `ready` و`remaining`. حين كان الرد يحمل المكافآت بلا
رصيد كانت الشاشة تعرضها صفًّا واحدًا بلا زر استبدال: العميل
الواقف عند الكاشير يرى عشرين سطرًا متطابقًا ولا يعرف أيها يصرفه
الآن، فيغلق التطبيق ويدفع بلا مكافأة.

لذلك يُثبَّت هنا أن `ready` تعني **قابلة للصرف فعلًا**: الرصيد
كافٍ والمخزون غير منتهٍ. أحدهما وحده يَعِد بما سيرفضه الخادم بعد
ضغطة واحدة — وهو أسوأ من ألا تظهر المكافأة أصلًا.
"""

from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.services import issue_tokens_for_customer
from apps.ledger.services import apply_entry
from tests import factories

pytestmark = pytest.mark.django_db


@pytest.fixture
def customer_api(customer):
    client = APIClient()
    tokens = issue_tokens_for_customer(customer)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


def earn(membership, program, amount: str) -> None:
    apply_entry(
        membership=membership,
        program=program,
        delta=Decimal(amount),
        reason="earn",
    )


def by_title(body):
    return {row["title"]: row for row in body}


class TestStanding:
    def test_balance_and_remaining_come_with_the_reward(self, customer_api, membership, program):
        earn(membership, program, "820")
        factories.RewardFactory(program=program, title="خصم ٥٠ جنيهًا", cost_amount=Decimal("1000"))

        row = customer_api.get(reverse("pos:my-rewards")).json()[0]

        assert row["balance"] == "820.00"
        assert row["remaining"] == "180.00"
        assert row["ready"] is False

    def test_enough_balance_is_ready(self, customer_api, membership, program):
        earn(membership, program, "500")
        factories.RewardFactory(program=program, cost_amount=Decimal("100"))

        row = customer_api.get(reverse("pos:my-rewards")).json()[0]

        assert row["ready"] is True
        assert row["remaining"] == "0.00"

    def test_a_member_with_no_balance_is_not_ready(self, customer_api, membership, program):
        """
        عضوية بلا رصيد ليست حالة نادرة — هي حال كل من انضمّ للتوّ.

        صفر مقابل صفر كان يمرّ كـ«جاهزة» في أي حساب يقسم بلا حارس.
        """
        factories.RewardFactory(program=program, cost_amount=Decimal("100"))

        row = customer_api.get(reverse("pos:my-rewards")).json()[0]

        assert row["balance"] == "0.00"
        assert row["ready"] is False
        assert row["progress"] == 0

    def test_progress_never_exceeds_one(self, customer_api, membership, program):
        """
        رصيد أكبر من التكلفة لا يعطي شريطًا بطول ٣٠٠٪.

        الشاشة تضرب هذه النسبة في عرض الشريط مباشرةً، وقيمة فوق
        الواحد تمدّه خارج بطاقته.
        """
        earn(membership, program, "3000")
        factories.RewardFactory(program=program, cost_amount=Decimal("1000"))

        row = customer_api.get(reverse("pos:my-rewards")).json()[0]

        assert row["progress"] == 1.0


class TestStock:
    def test_out_of_stock_is_never_ready(self, customer_api, membership, program):
        """
        رصيد كافٍ ومخزون منتهٍ ليس «جاهزة».

        زر الاستبدال كان سيظهر، ويردّ الخادم بالرفض بعد الضغط —
        العميل يكون قد قالها للكاشير بالفعل.
        """
        earn(membership, program, "500")
        factories.RewardFactory(program=program, cost_amount=Decimal("100"), stock=0)

        row = customer_api.get(reverse("pos:my-rewards")).json()[0]

        assert row["in_stock"] is False
        assert row["ready"] is False

    def test_unlimited_stock_is_in_stock(self, customer_api, membership, program):
        earn(membership, program, "500")
        factories.RewardFactory(program=program, cost_amount=Decimal("100"), stock=None)

        row = customer_api.get(reverse("pos:my-rewards")).json()[0]

        assert row["in_stock"] is True
        assert row["ready"] is True


class TestOrder:
    def test_ready_first_then_closest(self, customer_api, membership, program):
        """
        ترتيب الشاشة هو ترتيب ما يفعله العميل لا ترتيب التكلفة.

        الترتيب بالتكلفة كان يدفن المكافأة الجاهزة تحت أرخص منها
        وأبعد عنه — وهي أول ما يفتح الشاشة ليبحث عنه.
        """
        earn(membership, program, "300")
        factories.RewardFactory(program=program, title="بعيدة", cost_amount=Decimal("5000"))
        factories.RewardFactory(program=program, title="قريبة", cost_amount=Decimal("400"))
        factories.RewardFactory(program=program, title="جاهزة", cost_amount=Decimal("100"))

        titles = [row["title"] for row in customer_api.get(reverse("pos:my-rewards")).json()]

        assert titles == ["جاهزة", "قريبة", "بعيدة"]


class TestBrandIdentity:
    def test_each_row_carries_its_brand_colour(self, customer_api, membership, program, brand):
        """
        الصف يحمل لون علامته ومعرّفها.

        بلا اللون تصير القائمة صفوفًا متطابقة لا تربط المكافأة
        بالبطاقة الملوّنة في المحفظة، وبلا المعرّف لا يفتح الضغط
        على الصف بطاقته.
        """
        brand.primary_color = "#B0367A"
        brand.save(update_fields=["primary_color"])
        factories.RewardFactory(program=program)

        row = customer_api.get(reverse("pos:my-rewards")).json()[0]

        assert row["primary_color"] == "#B0367A"
        assert row["brand_id"] == str(brand.id)
        assert row["brand_name"] == brand.name

    def test_unit_label_follows_the_programme(self, customer_api, membership, program):
        """
        «١٠ أختام» لا «١٠ نقطة».

        الوحدة تأتي من البرنامج لا من ثابت في الواجهة: برنامج
        أختام يعرض مكافآته بوحدة النقاط يجعل الرقم بلا معنى.
        """
        factories.RewardFactory(program=program)

        row = customer_api.get(reverse("pos:my-rewards")).json()[0]

        assert row["unit_label"] == program.unit_label


class TestScope:
    def test_only_brands_the_customer_joined(self, customer_api, membership, program):
        """علامة لم ينضم إليها لا تظهر مكافآتها — ولو كان رصيده يكفيها."""
        mine = factories.RewardFactory(program=program, title="مكافأتي")

        stranger = factories.LoyaltyProgramFactory()
        factories.ProgramRuleFactory(program=stranger)
        factories.RewardFactory(program=stranger, title="مكافأة غريبة")

        titles = [row["title"] for row in customer_api.get(reverse("pos:my-rewards")).json()]

        assert titles == [mine.title]

    def test_balance_of_one_programme_does_not_leak_to_another(
        self, customer_api, customer, membership, program, brand
    ):
        """
        رصيد برنامج لا يفتح مكافآت برنامج آخر في نفس العلامة.

        قراءة رصيد العضوية جملةً بدل رصيد البرنامج كانت ستجعل
        أختام المقهى تصرف مكافأة مقاسة بالنقاط.
        """
        earn(membership, program, "900")

        other = factories.LoyaltyProgramFactory(brand=brand)
        factories.ProgramRuleFactory(program=other)
        factories.RewardFactory(program=other, title="برنامج ثانٍ", cost_amount=Decimal("100"))

        rows = by_title(customer_api.get(reverse("pos:my-rewards")).json())

        assert rows["برنامج ثانٍ"]["balance"] == "0.00"
        assert rows["برنامج ثانٍ"]["ready"] is False
