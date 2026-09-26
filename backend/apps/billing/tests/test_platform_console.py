"""
شاشات لوحة المنصة الأربع.

الخطر الأول هنا ليس رقمًا خاطئًا بل **تسريبًا**: لوحة المنصة
تُفتح بتوكن فريق المنصة، وأي مسار فيها ينسى صلاحيته يصير بابًا
يقرأ منه تاجر — أو عميل — بيانات كل التجّار. لذلك يُثبَّت الرفض
قبل المحتوى في كل مسار.

والخطر الثاني أن تعرض اللوحة طمأنة لا مصدر لها. شاشة التشغيل
تُفتح وقت الحادثة، ورقمٌ مخترَع فيها يوقف التحقيق في اللحظة التي
يجب أن يبدأ فيها. فلا يُعاد هنا إلا ما يمكن إثباته: هل استجابت
القاعدة، ومتى عملت كل مهمة، وهل الأرصدة مطابقة لقيودها.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.billing.models import Plan, Subscription
from apps.tenancy.models import StaffUser
from tests import factories

pytestmark = pytest.mark.django_db

User = get_user_model()

SCREENS = ["platform:health", "platform:users", "platform:ops", "platform:config"]


def api_for(user) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return client


@pytest.fixture
def platform_admin(db):
    user = User.objects.create_user(phone="+201000000099", password="x", full_name="فريق المنصة")
    user.is_platform_admin = True
    user.save(update_fields=["is_platform_admin"])
    return user


@pytest.fixture
def console(platform_admin) -> APIClient:
    return api_for(platform_admin)


class TestOnlyThePlatformTeamMayLook:
    @pytest.mark.parametrize("name", SCREENS)
    def test_anonymous_is_refused(self, name):
        assert APIClient().get(reverse(name)).status_code == 401

    @pytest.mark.parametrize("name", SCREENS)
    def test_a_merchant_owner_is_refused(self, name, branch):
        """
        صاحب متجر يرى متجره لا الشبكة.

        هذا هو الفرق بين لوحة تشغيل ومنفذ يقرأ منه تاجر أرقام
        منافسه.
        """
        owner = factories.StaffUserFactory(branch=branch, role=StaffUser.ROLE_OWNER)

        assert api_for(owner.user).get(reverse(name)).status_code == 403

    @pytest.mark.parametrize("name", SCREENS)
    def test_a_customer_is_refused(self, name, customer):
        from apps.accounts.services import issue_tokens_for_customer

        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {issue_tokens_for_customer(customer)['access']}"
        )

        assert client.get(reverse(name)).status_code == 403

    @pytest.mark.parametrize("name", SCREENS)
    def test_the_platform_team_may(self, name, console):
        assert console.get(reverse(name)).status_code == 200


class TestHealth:
    def test_every_metric_carries_its_target_and_verdict(self, console):
        """
        الرقم بلا هدفه لا يقول شيئًا.

        «انسحاب ٤٪» تُقرأ جيدة أو كارثية حسب الهدف، ولوحة تعرض
        الرقم وحده تترك القارئ يخمّن.
        """
        metrics = console.get(reverse("platform:health")).data["metrics"]

        assert metrics
        for metric in metrics:
            assert {"key", "label", "value", "target", "direction", "on_target"} <= set(metric)
            assert metric["direction"] in ("up", "down")

    def test_an_empty_platform_does_not_divide_by_zero(self, console):
        """أول يوم بعد النشر: صفر عملاء وصفر اشتراكات."""
        response = console.get(reverse("platform:health"))

        assert response.status_code == 200
        assert all(metric["value"] == 0 for metric in response.data["metrics"])

    def test_churn_is_judged_downward(self, console):
        """الانسحاب المؤشر الوحيد الذي الأقلّ فيه أفضل."""
        churn = next(
            m
            for m in console.get(reverse("platform:health")).data["metrics"]
            if m["key"] == "merchant_churn"
        )

        assert churn["direction"] == "down"
        assert churn["on_target"] is True  # صفر انسحاب

    def test_off_target_lists_only_what_missed(self, console, branch, customer):
        """
        القائمة المنفصلة هي ما يُقرأ أولًا.

        مؤشر خارج هدفه يستدعي قرارًا، ودفنه بين خمسة مؤشرات سليمة
        يجعله يُقرأ بعد أسبوع.
        """
        data = console.get(reverse("platform:health")).data

        assert all(not m["on_target"] for m in data["off_target"])

    def test_push_adoption_counts_only_subscribed_customers(self, console, customer):
        customer.push_subscription = {"endpoint": "https://example.test/p"}
        customer.save(update_fields=["push_subscription"])
        factories.CustomerFactory()  # بلا إشعارات

        push = next(
            m
            for m in console.get(reverse("platform:health")).data["metrics"]
            if m["key"] == "push_adoption"
        )

        assert push["value"] == 50.0

    def test_a_deleted_customer_does_not_drag_the_rates_down(self, console, customer):
        """
        المحذوف خرج من القاعدة ولا يُحسب في مقامها.

        عدّه يجعل معدّل التفعيل ينخفض كلما مارس عميل حقّه في
        الحذف — فيبدو المنتج يسوء لأن القانون احتُرم.
        """
        gone = factories.CustomerFactory()
        gone.anonymize()

        rate = next(
            m
            for m in console.get(reverse("platform:health")).data["metrics"]
            if m["key"] == "activation_rate"
        )

        assert rate["value"] == 0.0


class TestUsers:
    def test_it_lists_the_platform_team(self, console, platform_admin):
        data = console.get(reverse("platform:users")).data

        assert any(row["phone"] == platform_admin.phone for row in data["platform"])

    def test_it_lists_merchant_staff_with_their_brand(self, console, branch):
        member = factories.StaffUserFactory(branch=branch, role=StaffUser.ROLE_CASHIER)

        data = console.get(reverse("platform:users")).data

        row = next(r for r in data["staff"] if r["id"] == str(member.id))
        assert row["brand"] == branch.brand.name
        assert row["role_key"] == StaffUser.ROLE_CASHIER

    def test_it_does_not_list_end_customers(self, console, customer):
        """
        لوحة تشغيل لا دليل هواتف.

        بيانات العميل ملك التاجر وعميله، والمنصة وسيط — وعرضها
        هنا يكسر الفصل الذي يُباع للسلاسل كميزة.
        """
        body = str(console.get(reverse("platform:users")).data)

        assert customer.phone not in body


class TestOps:
    def test_the_database_reports_its_state(self, console):
        services = console.get(reverse("platform:ops")).data["services"]

        database = next(s for s in services if "قاعدة" in s["name"])
        assert database["ok"] is True
        assert database["latency_ms"] >= 0

    def test_integrity_sampling_sees_a_clean_ledger(self, console, membership, program):
        from apps.ledger.services import apply_entry

        apply_entry(membership=membership, program=program, delta=Decimal("100"), reason="earn")

        integrity = console.get(reverse("platform:ops")).data["integrity"]

        assert integrity["ok"] is True
        assert integrity["drifted"] == 0

    def test_integrity_sampling_catches_a_drifted_snapshot(self, console, membership, program):
        """
        الانحراف يعني مسارًا يكتب في الرصيد خارج المحرك.

        اللوحة تُفتح وقت الشك، وعرضها «سليم» على قاعدة منحرفة يوقف
        التحقيق في لحظة بدايته.
        """
        from apps.ledger.services import apply_entry
        from apps.loyalty.models import Balance

        apply_entry(membership=membership, program=program, delta=Decimal("100"), reason="earn")
        Balance.objects.filter(membership=membership, program=program).update(amount=Decimal("7"))

        integrity = console.get(reverse("platform:ops")).data["integrity"]

        assert integrity["ok"] is False
        assert integrity["drifted"] == 1

    def test_it_reports_no_uptime_it_cannot_measure(self, console):
        """
        لا APM في هذا النشر، فلا نسبة زمن تشغيل ولا متوسط استجابة.

        رقمٌ لا مصدر له في لوحة تشغيل يُقرأ كطمأنة، وهو أسوأ من
        غيابه.
        """
        body = console.get(reverse("platform:ops")).data

        assert "uptime" not in body
        assert "response_time" not in body


class TestConfig:
    def test_append_only_state_is_read_from_the_database(self, console):
        """
        «مفعَّل» يُقرأ من `pg_trigger` لا من قائمة مكتوبة بيد.

        لوحة امتثال تعلن حماية غير مثبّتة تجعل القارئ يتوقف عن
        التحقق — وهو بالضبط ما تُشترى اللوحة لمنعه.
        """
        privacy = console.get(reverse("platform:config")).data["privacy"]

        row = next(p for p in privacy if p["key"] == "append_only")
        assert isinstance(row["enabled"], bool)
        assert row["detail"]

    def test_every_plan_appears_with_its_limits(self, console):
        data = console.get(reverse("platform:config")).data

        codes = {plan["code"] for plan in data["plans"]}
        assert codes == {value for value, _ in Plan.choices}
        assert all("max_customers" in plan["limits"] for plan in data["plans"])

    def test_subscriber_counts_follow_the_active_subscriptions(self, console, brand):
        from django.utils import timezone

        Subscription.objects.filter(organization=brand.organization).delete()
        now = timezone.now()
        Subscription.objects.create(
            organization=brand.organization,
            plan=Plan.GROWTH,
            status=Subscription.STATUS_ACTIVE,
            mrr=Decimal("1200"),
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )

        plans = {
            p["code"]: p["subscribers"]
            for p in console.get(reverse("platform:config")).data["plans"]
        }

        assert plans[Plan.GROWTH] == 1
        assert plans[Plan.CHAIN] == 0

    def test_the_network_model_states_phase_one(self, console):
        """
        القرار المعماري غير الرجعي: رصيد منفصل لكل علامة.

        عرضه هنا ليس زينة — هو ما يمنع سؤال «هل نحن نظام مقاصة؟»
        من أن يُجاب عليه بالتخمين في اجتماع مع سلسلة.
        """
        model = console.get(reverse("platform:config")).data["network_model"]

        assert model["phase"] == 1
        assert [stage["status"] for stage in model["stages"]] == ["active", "planned", "blocked"]
