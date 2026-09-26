"""
شبكة التجّار والدليل العام.

الخطر في هذا المسار خطران متقابلان:
١. أن يتسرّب منه ما لا يجوز — الدليل مفتوح لأي زائر.
٢. أن يمسح `seed_network` عمل تاجر عند إعادة تشغيله في كل نشر.

معظم ما هنا يثبت أن أيًّا منهما لا يحدث.
"""

from decimal import Decimal

import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.db.models import Count
from django.urls import reverse
from rest_framework.test import APIClient

from apps.billing.models import Plan, Subscription
from apps.loyalty.models import LoyaltyProgram, ProgramRule, Reward
from apps.tenancy import geo, network
from apps.tenancy.models import Branch, Brand, Organization, Terminal
from tests import factories

pytestmark = pytest.mark.django_db


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def seeded():
    call_command("seed_network", verbosity=0)
    cache.delete("public:network:v1")


def _first_slug() -> str:
    return network.NETWORK[0].slug


# ══════════════ الكتالوج نفسه ══════════════


class TestCatalogueIntegrity:
    """
    أخطاء الكتالوج صامتة: إحداثي مقلوب يضع فرعًا في البحر، ورمز
    محافظة خاطئ يُسقطه من الخريطة بلا رسالة. تُكشف هنا لا هناك.
    """

    def test_slugs_unique(self):
        slugs = [brand.slug for brand in network.NETWORK]
        assert len(slugs) == len(set(slugs))

    def test_every_governorate_code_is_real(self):
        for brand in network.NETWORK:
            for branch in brand.branches:
                assert (
                    branch.governorate in geo.BY_CODE
                ), f"{brand.slug}/{branch.name}: محافظة مجهولة {branch.governorate}"

    def test_coordinates_inside_egypt(self):
        """حدود مصر تقريبًا: 22–32 شمالًا، 24–37 شرقًا."""
        for brand in network.NETWORK:
            for branch in brand.branches:
                assert 21.5 <= branch.lat <= 32.0, f"{brand.slug}/{branch.name}: خط عرض خارج مصر"
                assert 24.5 <= branch.lng <= 37.5, f"{brand.slug}/{branch.name}: خط طول خارج مصر"

    def test_coordinates_match_their_governorate(self):
        """
        الفرع داخل امتداد محافظته المعلن في `geo`.

        الخطأ الذي يكشفه: نسخ سطر فرع وتغيير اسم المدينة ونسيان
        الإحداثيات — فيظهر «فرع أسوان» فوق الإسكندرية على الخريطة.
        """
        for brand in network.NETWORK:
            for branch in brand.branches:
                anchor = geo.BY_CODE[branch.governorate]
                assert (
                    abs(branch.lat - anchor.anchor_lat) <= anchor.span
                ), f"{brand.slug}/{branch.name} بعيد عن {anchor.name}"
                assert (
                    abs(branch.lng - anchor.anchor_lng) <= anchor.span
                ), f"{brand.slug}/{branch.name} بعيد عن {anchor.name}"

    def test_branch_names_unique_within_brand(self):
        """المطابقة عند إعادة التشغيل بالاسم — تكراره يعني فرعًا لا يُحدَّث أبدًا."""
        for brand in network.NETWORK:
            names = [b.name for b in brand.branches]
            assert len(names) == len(set(names)), f"{brand.slug}: اسم فرع مكرّر"

    def test_every_brand_has_a_reward(self):
        """برنامج بلا مكافأة يجمع العميل فيه رصيدًا لا يستطيع صرفه."""
        for brand in network.NETWORK:
            assert brand.program.rewards, f"{brand.slug}: برنامج بلا مكافآت"

    def test_colors_are_hex(self):
        for brand in network.NETWORK:
            assert brand.color.startswith("#") and len(brand.color) == 7


# ══════════════ الزرع ══════════════


class TestSeeding:
    def test_creates_the_whole_network(self, seeded):
        assert Brand.objects.count() == len(network.NETWORK)
        assert Branch.objects.count() == network.branch_count()
        assert Terminal.objects.exists()
        assert LoyaltyProgram.objects.count() == len(network.NETWORK)
        assert Reward.objects.exists()

    def test_organizations_are_shared_not_duplicated(self, seeded):
        """علامتان لمؤسسة واحدة لا تنشئان مؤسستين بنفس الاسم."""
        names = {brand.organization for brand in network.NETWORK}
        assert Organization.objects.count() == len(names)

    def test_running_twice_changes_nothing(self, seeded):
        before = (Brand.objects.count(), Branch.objects.count(), Terminal.objects.count())

        call_command("seed_network", verbosity=0)

        assert (Brand.objects.count(), Branch.objects.count(), Terminal.objects.count()) == before

    def test_dry_run_writes_nothing(self):
        call_command("seed_network", "--dry-run", verbosity=0)

        assert Brand.objects.count() == 0

    def test_merchant_edits_survive_a_reseed(self, seeded):
        """
        التاجر غيّر اسم علامته ولونها من لوحته. النشر التالي لا
        يجوز أن يعيدهما إلى نص الكتالوج.
        """
        brand = Brand.objects.get(slug=_first_slug())
        brand.name = "اسم اختاره التاجر"
        brand.primary_color = "#123456"
        brand.save()

        call_command("seed_network", verbosity=0)

        brand.refresh_from_db()
        assert brand.name == "اسم اختاره التاجر"
        assert brand.primary_color == "#123456"

    def test_force_restores_the_catalogue(self, seeded):
        brand = Brand.objects.get(slug=_first_slug())
        brand.name = "اسم مؤقّت"
        brand.save()

        call_command("seed_network", "--force", verbosity=0)

        brand.refresh_from_db()
        assert brand.name == network.NETWORK[0].name

    def test_coordinates_are_corrected_on_reseed(self, seeded):
        """الإحداثيات ليست ملك التاجر — تصحيحها في الكتالوج يجب أن يصل."""
        branch = Branch.objects.filter(brand__slug=_first_slug()).first()
        branch.lat = Decimal("0")
        branch.save()

        call_command("seed_network", verbosity=0)

        branch.refresh_from_db()
        assert branch.lat != Decimal("0")

    def test_plan_fits_the_branch_count(self, seeded):
        """
        الحدّ الذي يمنع التاجر من إنشاء فرعه القادم لا يجوز أن يكون
        أقل ممّا زرعناه له بالفعل.
        """
        for brand in Brand.objects.select_related("organization"):
            count = Branch.objects.filter(brand=brand).count()
            subscription = Subscription.objects.get(organization=brand.organization)
            limit = subscription.limits["max_branches"]
            assert limit is None or limit >= count

    def test_subscriptions_are_active_and_priced(self, seeded):
        for subscription in Subscription.objects.all():
            assert subscription.status == Subscription.STATUS_ACTIVE
            assert subscription.mrr > 0

    def test_upgrade_is_never_reverted(self, seeded):
        organization = Organization.objects.first()
        subscription = Subscription.objects.get(organization=organization)
        subscription.plan = Plan.CHAIN
        subscription.save()

        call_command("seed_network", verbosity=0)

        subscription.refresh_from_db()
        assert subscription.plan == Plan.CHAIN

    def test_program_rules_are_not_rewritten(self, seeded):
        """
        تغيير `earn_rate` لبرنامج جارٍ يغيّر قيمة رصيد كسبه العملاء.
        النشر لا يفعل ذلك.
        """
        rule = ProgramRule.objects.first()
        rule.earn_rate = Decimal("99")
        rule.save()

        call_command("seed_network", verbosity=0)

        rule.refresh_from_db()
        assert rule.earn_rate == Decimal("99")

    def test_only_seeds_one_brand(self):
        call_command("seed_network", "--only", _first_slug(), verbosity=0)

        assert Brand.objects.count() == 1

    def test_prune_disables_but_never_deletes(self, seeded):
        brand = Brand.objects.get(slug=_first_slug())
        extra = Branch.objects.create(brand=brand, name="فرع أُغلق", lat=30, lng=31)

        call_command("seed_network", "--prune-branches", verbosity=0)

        extra.refresh_from_db()
        assert extra.is_active is False
        assert Branch.objects.filter(pk=extra.pk).exists()

    def test_prune_is_not_the_default(self, seeded):
        brand = Brand.objects.get(slug=_first_slug())
        extra = Branch.objects.create(brand=brand, name="فرع خارج الكتالوج", lat=30, lng=31)

        call_command("seed_network", verbosity=0)

        extra.refresh_from_db()
        assert extra.is_active is True


# ══════════════ الدليل العام ══════════════


class TestPublicDirectory:
    def test_open_without_a_token(self, api, seeded):
        response = api.get(reverse("public:network"))

        assert response.status_code == 200

    def test_counts_match_the_database(self, api, seeded):
        body = api.get(reverse("public:network")).json()

        assert body["stats"]["brands"] == Brand.objects.count()
        assert body["stats"]["branches"] == Branch.objects.filter(lat__isnull=False).count()

    def test_covers_many_governorates(self, api, seeded):
        body = api.get(reverse("public:network")).json()

        assert body["stats"]["governorates"] >= 15

    def test_every_point_is_plottable(self, api, seeded):
        """نقطة بلا إحداثي تكسر الخريطة أو تُرسم في زاويتها صامتة."""
        body = api.get(reverse("public:network")).json()

        for point in body["branches"]:
            assert isinstance(point["lat"], float)
            assert isinstance(point["lng"], float)
            assert point["governorate_name"]

    def test_governorates_list_is_complete(self, api, seeded):
        """المحافظات كلها تخرج ولو بصفر — الخريطة ترسم غير المغطّى أيضًا."""
        body = api.get(reverse("public:network")).json()

        assert len(body["governorates"]) == len(geo.GOVERNORATES)

    def test_categories_are_deduplicated(self, api, seeded):
        body = api.get(reverse("public:network")).json()

        assert len(body["categories"]) == len(set(body["categories"]))


class TestPublicDirectoryLeaks:
    """الضمان الأهم: لا شيء يخص عميلًا أو تشغيلًا يخرج من هنا."""

    FORBIDDEN = (
        "phone",
        "customer",
        "email",
        "balance",
        "transaction",
        "revenue",
        "mrr",
        "subscription",
        "staff",
        "pin",
        "terminal",
    )

    def test_payload_mentions_nothing_private(self, api, seeded):
        raw = api.get(reverse("public:network")).content.decode().lower()

        for word in self.FORBIDDEN:
            assert word not in raw, f"الدليل العام يذكر «{word}»"

    def test_unlisted_brand_is_hidden(self, api, seeded):
        brand = Brand.objects.get(slug=_first_slug())
        brand.is_listed = False
        brand.save()

        body = api.get(reverse("public:network")).json()

        assert all(item["slug"] != brand.slug for item in body["brands"])
        assert all(point["brand_slug"] != brand.slug for point in body["branches"])

    def test_inactive_brand_is_hidden(self, api, seeded):
        brand = Brand.objects.get(slug=_first_slug())
        brand.is_active = False
        brand.save()

        body = api.get(reverse("public:network")).json()

        assert all(item["slug"] != brand.slug for item in body["brands"])

    def test_inactive_branch_is_hidden(self, api, seeded):
        branch = Branch.objects.filter(brand__slug=_first_slug()).first()
        branch.is_active = False
        branch.save()

        body = api.get(reverse("public:network")).json()

        assert all(point["id"] != str(branch.id) for point in body["branches"])

    def test_member_count_is_rounded(self, api, seeded, customer, brand):
        """العدد الدقيق يتحوّل إلى قناة تسريب عند مراقبته."""
        from apps.tenancy.public_views import _rounded

        assert _rounded(12_437) == 12_400
        assert _rounded(99) == 99

    def test_brand_without_plottable_branches_is_hidden(self, api, seeded):
        """
        علامة تعاقدت ولم تفتح فرعًا بإحداثيات: عدّها في «١٥ متجرًا»
        يجعل الرقم على الصفحة العامة أكبر ممّا تستطيع الخريطة إثباته.
        """
        brand = Brand.objects.create(
            organization=Organization.objects.first(),
            slug="lam-yaftah-baad",
            name="علامة لم تفتح بعد",
        )

        body = api.get(reverse("public:network")).json()

        assert all(item["slug"] != brand.slug for item in body["brands"])


class TestDirectoryCache:
    def test_a_new_branch_appears_immediately(self, api, seeded):
        """
        بلا إبطال الذاكرة يفتتح التاجر فرعًا ولا يراه، فيعيد إنشاءه
        ظنًّا أن الحفظ فشل — فرعان متطابقان في نفس الحي.
        """
        api.get(reverse("public:network"))  # يملأ الذاكرة

        brand = Brand.objects.get(slug=_first_slug())
        Branch.objects.create(
            brand=brand, name="فرع افتُتح للتو", city="بنها", governorate="QLY", lat=30.46, lng=31.18
        )

        body = api.get(reverse("public:network")).json()

        assert any(point["name"] == "فرع افتُتح للتو" for point in body["branches"])

    def test_response_is_publicly_cacheable(self, api, seeded):
        response = api.get(reverse("public:network"))

        assert "public" in response["Cache-Control"]


class TestDemoPlanFitsTheBrand:
    """
    باقة حساب التجربة تتّسع لفروع علامته.

    تثبيتها على «نمو» كان يضع علامة بسبعة عشر فرعًا على باقة حدّها
    خمسة: شاشة الاشتراك تفتح على شريطين أحمرين، وأول محاولة لإضافة
    فرع تفشل — عطل يبدو في العرض كأنه عطل في المنتج.
    """

    def test_wide_brand_gets_a_plan_that_fits(self, db):
        from apps.billing.models import Subscription
        from apps.tenancy.models import Branch, Brand

        call_command("seed_network", verbosity=0)
        call_command("demo_accounts", verbosity=0)

        brand = (
            Brand.objects.annotate(reach=Count("branches")).order_by("-reach", "created_at").first()
        )
        count = Branch.objects.filter(brand=brand).count()
        subscription = Subscription.objects.get(organization=brand.organization)
        limit = subscription.limits["max_branches"]

        assert limit is None or limit >= count

    def test_small_brand_is_not_over_provisioned(self, db, brand):
        """علامة بفرع واحد لا تُرفَع إلى «سلاسل» بلا سبب."""
        from apps.billing.models import Plan, Subscription

        factories.BranchFactory(brand=brand)
        call_command("demo_accounts", "--brand-slug", brand.slug, verbosity=0)

        subscription = Subscription.objects.get(organization=brand.organization)

        assert subscription.plan == Plan.STARTER

    def test_mrr_matches_the_plan(self, db, brand):
        from apps.billing.models import PLAN_LIMITS, Subscription

        factories.BranchFactory(brand=brand)
        call_command("demo_accounts", "--brand-slug", brand.slug, verbosity=0)

        subscription = Subscription.objects.get(organization=brand.organization)

        assert subscription.mrr == PLAN_LIMITS[subscription.plan]["monthly_price"]
