"""
الحملات: الشرائح وموجّه القنوات والتكلفة.

القاعدة الحاكمة في كل هذه الاختبارات: **الرقم الذي يراه التاجر قبل
الإرسال هو الرقم الذي سيدفعه.**
"""

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.billing.models import MessageCredit, Plan
from apps.billing.services import apply_credit, get_subscription, wallet_balance
from apps.campaigns import router, segments, services
from apps.campaigns.models import Campaign, Channel, MessageJob
from apps.common.exceptions import InvalidState
from apps.ledger.services import apply_entry
from tests import factories

pytestmark = pytest.mark.django_db


@pytest.fixture
def paid_brand(brand):
    """علامة على باقة تسمح بالحملات ولديها رصيد رسائل."""
    subscription = get_subscription(brand.organization)
    subscription.plan = Plan.GROWTH
    subscription.save(update_fields=["plan"])

    apply_credit(
        organization=brand.organization,
        delta=1_000,
        reason=MessageCredit.REASON_TOPUP,
    )
    return brand


def _member(brand, *, push=False, consent=True, name="عميل"):
    customer = factories.CustomerFactory(
        full_name=name,
        consent_at=timezone.now() if consent else None,
        push_subscription={"endpoint": "https://push.example/x"} if push else None,
    )
    return factories.MembershipFactory(customer=customer, brand=brand)


# ═══════════════════════ الشرائح ═══════════════════════


class TestSegmentValidation:
    def test_unknown_key_rejected(self):
        """
        المفتاح المجهول يُرفض لا يُتجاهَل: تجاهله يعني إرسال حملة
        لشريحة أوسع مما قصده التاجر — وفاتورة أكبر.
        """
        with pytest.raises(segments.InvalidSegment):
            segments.validate({"delete_everything": True})

    def test_negative_value_rejected(self):
        with pytest.raises(segments.InvalidSegment):
            segments.validate({"inactive_days": -5})

    def test_non_numeric_rejected(self):
        with pytest.raises(segments.InvalidSegment):
            segments.validate({"inactive_days": "كثير"})

    def test_inverted_balance_range_rejected(self):
        with pytest.raises(segments.InvalidSegment):
            segments.validate({"min_balance": 500, "max_balance": 100})

    def test_empty_is_valid(self):
        assert segments.validate({}) == {}

    def test_not_a_dict_rejected(self):
        with pytest.raises(segments.InvalidSegment):
            segments.validate(["inactive_days"])


class TestSegmentResolution:
    def test_consent_is_mandatory(self, brand):
        """عميل بلا موافقة لا يدخل أي شريحة مهما طابق البقية."""
        _member(brand, consent=True)
        _member(brand, consent=False)

        assert segments.resolve(brand, {}).count() == 1

    def test_deleted_customer_excluded(self, brand):
        member = _member(brand)
        member.customer.deleted_at = timezone.now()
        member.customer.save(update_fields=["deleted_at"])

        assert segments.resolve(brand, {}).count() == 0

    def test_other_brand_excluded(self, brand):
        _member(brand)
        _member(factories.BrandFactory())

        assert segments.resolve(brand, {}).count() == 1

    def test_never_active_counts_as_dormant(self, brand, program):
        """
        من لم يتعامل قط يُعدّ خاملًا — وهو غالبًا أهم مستهدَف:
        سجّل ولم يعد.
        """
        _member(brand)

        assert segments.resolve(brand, {"inactive_days": 30}).count() == 1

    def test_recent_activity_excludes_from_dormant(self, brand, program):
        member = _member(brand)
        apply_entry(membership=member, program=program, delta=Decimal("10"), reason="earn")

        assert segments.resolve(brand, {"inactive_days": 30}).count() == 0
        assert segments.resolve(brand, {"active_within_days": 30}).count() == 1

    def test_balance_range(self, brand, program):
        low = _member(brand, name="قليل")
        high = _member(brand, name="كثير")
        apply_entry(membership=low, program=program, delta=Decimal("50"), reason="earn")
        apply_entry(membership=high, program=program, delta=Decimal("500"), reason="earn")

        result = segments.resolve(brand, {"min_balance": 100})

        assert [m.customer.full_name for m in result] == ["كثير"]

    def test_joined_within_days(self, brand):
        _member(brand)

        assert segments.resolve(brand, {"joined_within_days": 1}).count() == 1

    def test_describe_is_readable(self):
        assert "٣٠" in segments.describe({"inactive_days": 30}) or "30" in segments.describe(
            {"inactive_days": 30}
        )
        assert segments.describe({}) == "كل عملاء العلامة الموافقين على التواصل"


# ═══════════════════════ الموجّه ═══════════════════════


class TestChannelRouter:
    def test_push_preferred_when_available(self, brand):
        member = _member(brand, push=True)

        route = router.pick_channel(member.customer)

        assert route.channel == Channel.PUSH
        assert route.cost == Decimal("0")

    def test_falls_back_to_whatsapp(self, brand):
        member = _member(brand, push=False)

        route = router.pick_channel(member.customer)

        assert route.channel == Channel.WHATSAPP
        assert route.cost > 0

    def test_respects_custom_priority(self, brand):
        member = _member(brand, push=True)

        route = router.pick_channel(member.customer, [Channel.SMS])

        assert route.channel == Channel.SMS

    def test_anonymized_customer_unreachable(self, brand):
        member = _member(brand)
        member.customer.anonymize()

        route = router.pick_channel(member.customer, [Channel.SMS])

        assert route.reachable is False
        assert route.cost == Decimal("0")

    def test_estimate_splits_by_channel(self, paid_brand):
        for _ in range(3):
            _member(paid_brand, push=True)
        for _ in range(2):
            _member(paid_brand, push=False)

        quote = router.estimate(segments.resolve(paid_brand, {}))

        assert quote.recipients == 5
        assert quote.reachable == 5
        assert quote.per_channel[Channel.PUSH] == 3
        assert quote.per_channel[Channel.WHATSAPP] == 2
        # ثلاث مجانية واثنتان مدفوعتان
        assert quote.billable_messages == 2
        assert quote.cost == Decimal("0.70")

    def test_unreachable_costs_nothing(self, brand):
        member = _member(brand)
        member.customer.anonymize()

        quote = router.estimate(segments.resolve(brand, {}))

        assert quote.cost == Decimal("0")

    def test_render_fills_placeholders(self, brand):
        member = _member(brand, name="سارة")

        body = router.render(
            "أهلًا {name}، رصيدك في {brand} هو {balance}",
            customer=member.customer,
            brand=brand,
            balance="120",
        )

        assert "سارة" in body
        assert brand.name in body
        assert "120" in body

    def test_render_survives_unknown_placeholder(self, brand):
        """متغيّر مجهول يظهر كما هو ولا يُسقِط الحملة كلها."""
        member = _member(brand)

        body = router.render("{name} — {unknown}", customer=member.customer, brand=brand)

        assert "{unknown}" in body

    def test_render_uses_fallback_name(self, brand):
        member = _member(brand, name="")

        body = router.render("{name}", customer=member.customer, brand=brand)

        assert body == "عميلنا العزيز"


# ═══════════════════════ دورة الحملة ═══════════════════════


class TestCampaignLifecycle:
    def test_free_plan_cannot_create(self, brand, cashier):
        from apps.billing.services import FeatureNotInPlan

        with pytest.raises(FeatureNotInPlan):
            services.create_campaign(
                brand=brand,
                staff_user=cashier,
                name="حملة",
                message_template="مرحبًا",
                segment_query={},
            )

    def test_create_returns_estimate(self, paid_brand, cashier):
        _member(paid_brand, push=True)
        _member(paid_brand, push=False)

        campaign, quote = services.create_campaign(
            brand=paid_brand,
            staff_user=cashier,
            name="عودة العملاء",
            message_template="اشتقنا لك يا {name}",
            segment_query={},
        )

        assert campaign.status == Campaign.STATUS_DRAFT
        assert campaign.estimated_recipients == 2
        assert campaign.estimated_cost == quote.cost

    def test_invalid_segment_rejected_at_creation(self, paid_brand, cashier):
        with pytest.raises(services.CampaignError) as exc:
            services.create_campaign(
                brand=paid_brand,
                staff_user=cashier,
                name="حملة",
                message_template="مرحبًا",
                segment_query={"nope": 1},
            )
        assert exc.value.code == "invalid_segment"

    def test_scheduled_when_time_given(self, paid_brand, cashier):
        campaign, _ = services.create_campaign(
            brand=paid_brand,
            staff_user=cashier,
            name="حملة مجدولة",
            message_template="مرحبًا",
            segment_query={},
            scheduled_at=timezone.now() + timezone.timedelta(hours=2),
        )

        assert campaign.status == Campaign.STATUS_SCHEDULED

    def test_preview_writes_nothing(self, paid_brand):
        _member(paid_brand, push=True)

        result = services.preview(paid_brand, {})

        assert result["reachable"] == 1
        assert result["wallet_balance"] == 1_000
        assert "segment_description" in result
        assert Campaign.objects.count() == 0

    def test_send_creates_jobs_and_charges_once(self, paid_brand, cashier):
        for _ in range(2):
            _member(paid_brand, push=True)
        for _ in range(3):
            _member(paid_brand, push=False)

        campaign, _ = services.create_campaign(
            brand=paid_brand,
            staff_user=cashier,
            name="حملة",
            message_template="مرحبًا {name}",
            segment_query={},
        )

        result = services.send_campaign(campaign.id)

        assert result["sent"] == 5
        assert MessageJob.objects.filter(campaign=campaign).count() == 5
        # ثلاث مدفوعة فقط — الإشعارات مجانية
        assert wallet_balance(paid_brand.organization) == 997

        campaign.refresh_from_db()
        assert campaign.status == Campaign.STATUS_SENT
        assert campaign.finished_at is not None

    def test_double_send_rejected(self, paid_brand, cashier):
        _member(paid_brand, push=True)
        campaign, _ = services.create_campaign(
            brand=paid_brand,
            staff_user=cashier,
            name="حملة",
            message_template="مرحبًا",
            segment_query={},
        )
        services.send_campaign(campaign.id)

        with pytest.raises(InvalidState) as exc:
            services.send_campaign(campaign.id)
        assert exc.value.code == "already_sent"

    def test_recipient_appears_once(self, paid_brand, cashier):
        member = _member(paid_brand, push=True)
        campaign, _ = services.create_campaign(
            brand=paid_brand,
            staff_user=cashier,
            name="حملة",
            message_template="مرحبًا",
            segment_query={},
        )
        services.send_campaign(campaign.id)

        assert MessageJob.objects.filter(campaign=campaign, customer=member.customer).count() == 1

    def test_insufficient_credits_blocks_send(self, brand, cashier):
        subscription = get_subscription(brand.organization)
        subscription.plan = Plan.STARTER
        subscription.save(update_fields=["plan"])
        apply_credit(organization=brand.organization, delta=1, reason=MessageCredit.REASON_TOPUP)

        for _ in range(3):
            _member(brand, push=False)

        campaign, _ = services.create_campaign(
            brand=brand,
            staff_user=cashier,
            name="حملة",
            message_template="مرحبًا",
            segment_query={},
        )

        from apps.billing.services import InsufficientCredits

        with pytest.raises(InsufficientCredits):
            services.send_campaign(campaign.id)

        # لا رسالة أُرسلت ولا رصيد خُصم
        assert MessageJob.objects.filter(status=MessageJob.STATUS_SENT).count() == 0
        assert wallet_balance(brand.organization) == 1

    def test_unreachable_recipients_skipped(self, paid_brand, cashier):
        reachable = _member(paid_brand, push=True)
        unreachable = _member(paid_brand)
        unreachable.customer.anonymize()

        campaign, _ = services.create_campaign(
            brand=paid_brand,
            staff_user=cashier,
            name="حملة",
            message_template="مرحبًا",
            segment_query={},
        )
        services.send_campaign(campaign.id)

        jobs = MessageJob.objects.filter(campaign=campaign)
        assert jobs.count() == 1
        assert jobs.first().customer_id == reachable.customer_id

    def test_failed_messages_are_refunded(self, paid_brand, cashier, monkeypatch):
        """
        خصم رصيد مقابل رسالة لم تصل هو أخذ مال بلا خدمة.
        الاسترداد إلزامي لا مجاملة.
        """
        for _ in range(2):
            _member(paid_brand, push=False)

        campaign, _ = services.create_campaign(
            brand=paid_brand,
            staff_user=cashier,
            name="حملة",
            message_template="مرحبًا",
            segment_query={},
        )

        def _explode(self, *, phone, body):
            raise RuntimeError("المزوّد لا يستجيب")

        from apps.campaigns.providers.console import ConsoleWhatsAppProvider

        monkeypatch.setattr(ConsoleWhatsAppProvider, "send", _explode)

        result = services.send_campaign(campaign.id)

        assert result["failed"] == 2
        assert result["refunded"] == 2
        # خُصم ٢ ثم استُرد ٢
        assert wallet_balance(paid_brand.organization) == 1_000

    def test_cancel_before_send(self, paid_brand, cashier):
        campaign, _ = services.create_campaign(
            brand=paid_brand,
            staff_user=cashier,
            name="حملة",
            message_template="مرحبًا",
            segment_query={},
        )

        cancelled = services.cancel_campaign(campaign.id, staff_user=cashier)

        assert cancelled.status == Campaign.STATUS_CANCELLED

    def test_cancel_after_send_rejected(self, paid_brand, cashier):
        _member(paid_brand, push=True)
        campaign, _ = services.create_campaign(
            brand=paid_brand,
            staff_user=cashier,
            name="حملة",
            message_template="مرحبًا",
            segment_query={},
        )
        services.send_campaign(campaign.id)

        with pytest.raises(InvalidState):
            services.cancel_campaign(campaign.id, staff_user=cashier)

    def test_cancelled_cannot_be_sent(self, paid_brand, cashier):
        campaign, _ = services.create_campaign(
            brand=paid_brand,
            staff_user=cashier,
            name="حملة",
            message_template="مرحبًا",
            segment_query={},
        )
        services.cancel_campaign(campaign.id, staff_user=cashier)

        with pytest.raises(InvalidState) as exc:
            services.send_campaign(campaign.id)
        assert exc.value.code == "cancelled"


class TestOperationalNotify:
    def test_free_channel_only(self, brand):
        """تنبيه خدمي لا يخصم رصيدًا مدفوعًا بلا طلب التاجر."""
        member = _member(brand, push=True)

        assert services.notify_one(customer=member.customer, brand=brand, body="رصيدك ينتهي قريبًا")

    def test_paid_channel_refused(self, brand):
        member = _member(brand, push=False)

        assert (
            services.notify_one(
                customer=member.customer,
                brand=brand,
                body="تنبيه",
                channel=Channel.SMS,
            )
            is False
        )
