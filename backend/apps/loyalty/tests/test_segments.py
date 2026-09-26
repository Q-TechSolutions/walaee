"""
شرائح العملاء في قائمة لوحة التاجر.

الخطر هنا ليس رقمًا خاطئًا بل رقمًا **يبدو صحيحًا**. شريحة لا
تعرفها الخلفية كانت تُعاد بلا تصفية، فتقرأ اللوحة «١٬٢٥١ عميلًا
معرّضًا للفقدان» وتحتها قائمة انضمّ أصحابها أمس. لا شيء يتعطّل،
ولا سطر في السجل — فقط تاجر يطلق حملة استرجاع على قاعدته كاملة.

لذلك يُثبَّت هنا أمران: أن الشريحة المجهولة تُرفَض، وأن تعريف
«معرّض للفقدان» هو ما تقوله الشاشة حرفيًا — نسبيًّا لعادة العميل
لا مطلقًا للجميع.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.ledger.models import LedgerEntry, Transaction
from apps.ledger.services import apply_entry
from apps.tenancy.models import StaffUser
from tests import factories

pytestmark = pytest.mark.django_db


@pytest.fixture
def manager(branch):
    return factories.StaffUserFactory(branch=branch, role=StaffUser.ROLE_MANAGER)


@pytest.fixture
def client(manager) -> APIClient:
    api = APIClient()
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(manager.user).access_token}")
    return api


def visit(membership, program, terminal, *, days_ago: int):
    """
    زيارة مؤرَّخة في الماضي: عملية مؤكّدة وقيدها.

    عبر `apply_entry` لا بإنشاء القيد مباشرةً — الشريحة تقرأ
    القيود، وقيد بلا رصيد يقابله يجعل الاختبار يمرّ على بيانات
    لا يمكن أن توجد في الإنتاج.
    """
    moment = timezone.now() - timedelta(days=days_ago)
    txn = Transaction.objects.create(
        terminal=terminal,
        customer=membership.customer,
        invoice_no=f"T{days_ago}-{membership.pk.hex[:6]}",
        invoice_amount=Decimal("100"),
        status=Transaction.STATUS_CONFIRMED,
        confirmed_at=moment,
        created_at=moment,
    )
    entry = apply_entry(
        membership=membership,
        program=program,
        delta=Decimal("100"),
        reason=LedgerEntry.REASON_EARN,
        transaction_obj=txn,
    )
    LedgerEntry.objects.filter(pk=entry.pk).update(created_at=moment)
    return txn


def names(response):
    return {row["full_name"] for row in response.data["results"]}


class TestUnknownSegmentIsRefused:
    """
    الشريحة المجهولة خطأ، لا «كل العملاء».

    هذا هو العطل الأصلي: اللوحة طلبت `at_risk` قبل أن تُنفَّذ،
    والخلفية ردّت بالقاعدة كاملة. الرد الصامت بكل شيء أسوأ من
    الرفض لأنه يمرّ في المراجعة ويظهر رقمًا يصدّقه التاجر.
    """

    def test_it_returns_400_not_everyone(self, client, manager, brand):
        factories.MembershipFactory(brand=brand)
        factories.MembershipFactory(brand=brand)

        response = client.get(reverse("loyalty:customers"), {"segment": "vip"})

        assert response.status_code == 400
        assert "segment" in response.data["error"]["details"]

    def test_known_segments_still_pass(self, client, brand):
        factories.MembershipFactory(brand=brand)

        for segment in ("active", "dormant", "new", "at_risk"):
            assert client.get(reverse("loyalty:customers"), {"segment": segment}).status_code == 200

    def test_no_segment_returns_everyone(self, client, brand):
        factories.MembershipFactory(brand=brand)
        factories.MembershipFactory(brand=brand)

        response = client.get(reverse("loyalty:customers"))

        assert response.data["count"] == 2


class TestAtRiskIsRelativeToHabit:
    """
    «لم يعودوا خلال ضعف متوسط فترة زيارتهم المعتادة».

    عتبة مطلقة (٩٠ يومًا مثلًا) تفشل في الاتجاهين: تفوّت عميلًا
    أسبوعيًا صمت شهرًا — وقد فُقد فعلًا — وتُدرج عميلًا موسميًا
    يشتري مرتين في السنة وهو لم يتأخر أصلًا.
    """

    def test_a_weekly_customer_gone_a_month_is_at_risk(self, client, brand, program, terminal):
        weekly = factories.MembershipFactory(
            brand=brand, customer=factories.CustomerFactory(full_name="أسبوعي")
        )
        for days in (120, 113, 106, 99, 92, 85, 78, 71, 64, 30):
            visit(weekly, program, terminal, days_ago=days)

        response = client.get(reverse("loyalty:customers"), {"segment": "at_risk"})

        assert "أسبوعي" in names(response)

    def test_a_seasonal_customer_on_schedule_is_not(self, client, brand, program, terminal):
        """يشتري كل ستة أشهر، وآخر زيارة قبل شهر — في موعده تمامًا."""
        seasonal = factories.MembershipFactory(
            brand=brand, customer=factories.CustomerFactory(full_name="موسمي")
        )
        for days in (390, 210, 30):
            visit(seasonal, program, terminal, days_ago=days)

        response = client.get(reverse("loyalty:customers"), {"segment": "at_risk"})

        assert "موسمي" not in names(response)

    def test_one_visit_is_not_enough_to_have_a_habit(self, client, brand, program, terminal):
        """
        زيارة واحدة لا تُنتج «فترة معتادة».

        إدراجه كان سيغرق الشريحة بكل من جرّب المتجر مرة — وهم
        أكثر من يحتاجون حملة ترحيب لا حملة استرجاع.
        """
        once = factories.MembershipFactory(
            brand=brand, customer=factories.CustomerFactory(full_name="مرة واحدة")
        )
        visit(once, program, terminal, days_ago=200)

        response = client.get(reverse("loyalty:customers"), {"segment": "at_risk"})

        assert "مرة واحدة" not in names(response)

    def test_a_brand_new_member_is_not_at_risk(self, client, brand, program, terminal):
        """
        العطل كما ظهر في اللوحة: عضو انضمّ أمس في صدارة القائمة.
        """
        fresh = factories.MembershipFactory(
            brand=brand, customer=factories.CustomerFactory(full_name="جديد")
        )
        visit(fresh, program, terminal, days_ago=1)
        visit(fresh, program, terminal, days_ago=0)

        response = client.get(reverse("loyalty:customers"), {"segment": "at_risk"})

        assert "جديد" not in names(response)

    def test_the_welcome_bonus_does_not_count_as_a_visit(self, client, brand, program, terminal):
        """
        مكافأة الانضمام قيد بلا عملية.

        عدّها زيارةً كان يعطي كل عميل زار مرة «زيارتين»، فيصير له
        «فترة معتادة» مصطنعة طولها صفر — وكل عميل جديد يسقط في
        شريحة المعرّضين للفقدان من يومه الأول.
        """
        member = factories.MembershipFactory(
            brand=brand, customer=factories.CustomerFactory(full_name="بمكافأة")
        )
        bonus = apply_entry(
            membership=member,
            program=program,
            delta=Decimal("100"),
            reason=LedgerEntry.REASON_WELCOME,
        )
        moment = timezone.now() - timedelta(days=200)
        LedgerEntry.objects.filter(pk=bonus.pk).update(created_at=moment)
        visit(member, program, terminal, days_ago=200)

        response = client.get(reverse("loyalty:customers"), {"segment": "at_risk"})

        assert "بمكافأة" not in names(response)

    def test_the_longest_silent_customer_comes_first(self, client, brand, program, terminal):
        """
        الترتيب بآخر زيارة صاعدًا.

        اللوحة تعرض أربعة صفوف فقط، فترتيبها هو ما يحدّد من يراه
        التاجر — والأطول صمتًا هو الأقرب إلى الضياع نهائيًا.
        """
        # كلاهما معرّض للفقدان: عادته عشرة أيام وصمته مئات.
        # لو كان أحدهما في موعده لسقط من الشريحة ولم يُختبَر الترتيب.
        for label, last in (("أقدم", 380), ("أحدث", 180)):
            member = factories.MembershipFactory(
                brand=brand, customer=factories.CustomerFactory(full_name=label)
            )
            visit(member, program, terminal, days_ago=last + 20)
            visit(member, program, terminal, days_ago=last + 10)
            visit(member, program, terminal, days_ago=last)

        response = client.get(reverse("loyalty:customers"), {"segment": "at_risk"})
        ordered = [row["full_name"] for row in response.data["results"]]

        assert ordered.index("أقدم") < ordered.index("أحدث")
