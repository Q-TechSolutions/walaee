"""
حساب العميل: المحفظة والنشاط والخصوصية.

اختبارات الخصوصية هنا ليست شكلية: التصدير والحذف شرطان للامتثال،
وكسرهما لا يظهر في أي شاشة حتى يطلبهما عميل فعليًا.
"""

from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Customer, OtpCode
from apps.accounts.services import issue_tokens_for_customer
from apps.ledger.services import apply_entry, redeem_reward
from apps.pos import codes, services
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
    membership = factories.MembershipFactory(customer=customer, brand=brand)
    apply_entry(membership=membership, program=program, delta=Decimal("250"), reason="earn")
    return membership


class TestProfile:
    def test_read(self, me, customer):
        body = me.get(reverse("me:profile")).json()

        assert body["phone"] == customer.phone
        assert "has_consent" in body

    def test_update_name(self, me):
        body = me.patch(reverse("me:profile"), {"full_name": "سارة أحمد"}, format="json").json()

        assert body["full_name"] == "سارة أحمد"

    def test_phone_is_read_only(self, me, customer):
        """تغيير الهاتف يعني انتحال هوية عميل آخر — مرفوض دائمًا."""
        me.patch(reverse("me:profile"), {"phone": "01099999999"}, format="json")

        customer.refresh_from_db()
        assert customer.phone != "+201099999999"


class TestWallet:
    def test_cards_list_with_balances(self, me, card, brand):
        body = me.get(reverse("me:cards")).json()

        assert len(body) == 1
        assert body[0]["brand_name"] == brand.name
        assert body[0]["balances"][0]["amount"] == "250.00"
        assert body[0]["primary_color"]

    def test_empty_wallet(self, me):
        assert me.get(reverse("me:cards")).json() == []

    def test_card_detail_includes_rewards_and_activity(self, me, card, brand, program):
        factories.RewardFactory(program=program, title="قهوة مجانية")

        body = me.get(reverse("me:card", args=[brand.id])).json()

        assert body["brand_name"] == brand.name
        assert body["rewards"][0]["title"] == "قهوة مجانية"
        assert len(body["activity"]) == 1
        assert body["activity"][0]["delta"] == "250.00"

    def test_card_of_unjoined_brand_is_404(self, me):
        other = factories.BrandFactory()

        response = me.get(reverse("me:card", args=[other.id]))

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_a_member"

    def test_summary_counts(self, me, card):
        body = me.get(reverse("me:summary")).json()

        assert body["cards"] == 1
        assert body["by_type"]["points"] == "250.00"
        assert body["pending_redemptions"] == 0

    def test_activity_is_paginated(self, me, card, program):
        for _ in range(3):
            apply_entry(membership=card, program=program, delta=Decimal("5"), reason="earn")

        body = me.get(reverse("me:activity")).json()

        assert body["count"] == 4
        assert body["results"][0]["brand_name"]

    def test_redemption_codes_listed(self, me, card, program, brand):
        reward = factories.RewardFactory(program=program, cost_amount=Decimal("100"))
        redeem_reward(membership=card, reward=reward)

        body = me.get(reverse("me:redemptions")).json()

        assert len(body) == 1
        assert body[0]["status"] == "pending"
        assert body[0]["brand_name"] == brand.name


class TestPushSubscription:
    def test_register(self, me, customer):
        response = me.post(
            reverse("me:push"),
            {"subscription": {"endpoint": "https://push.example/abc", "keys": {}}},
            format="json",
        )

        assert response.json() == {"enabled": True}
        customer.refresh_from_db()
        assert customer.push_subscription["endpoint"] == "https://push.example/abc"

    def test_invalid_payload_rejected(self, me):
        response = me.post(reverse("me:push"), {"subscription": "nope"}, format="json")

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "invalid_subscription"

    def test_unregister(self, me, customer):
        customer.push_subscription = {"endpoint": "x"}
        customer.save(update_fields=["push_subscription"])

        assert me.delete(reverse("me:push")).json() == {"enabled": False}


class TestDataExport:
    def test_includes_everything(self, me, card, brand, terminal, cashier, customer, program):
        code = codes.issue_code(terminal.id)
        txn = services.create_transaction(
            code=code, customer=customer, invoice_amount=Decimal("90"), invoice_no="EX-1"
        )
        services.confirm_transaction(txn.id, staff_user=cashier)

        body = me.get(reverse("me:export")).json()

        assert body["profile"]["phone"] == customer.phone
        assert body["memberships"][0]["brand"] == brand.name
        assert len(body["ledger"]) >= 1
        assert body["transactions"][0]["invoice_no"] == "EX-1"
        assert "generated_at" in body


class TestAccountDeletion:
    def test_requires_fresh_code(self, me, customer):
        """جلسة مفتوحة لا تكفي: هاتف في يد شخص آخر لا يمحو الحساب."""
        response = me.delete(reverse("me:delete"), {"code": "000000"}, format="json")

        assert response.status_code == 410
        assert response.json()["error"]["code"] == "otp_not_found"

    def test_request_then_confirm(self, me, customer, card, program):
        from django.contrib.auth.hashers import make_password

        assert me.post(reverse("me:delete")).json() == {"sent": True}

        OtpCode.objects.filter(phone=customer.phone, purpose=OtpCode.PURPOSE_DELETE).update(
            code_hash=make_password("654321")
        )

        response = me.delete(reverse("me:delete"), {"code": "654321"}, format="json")

        assert response.status_code == 200
        assert response.json()["deleted"] is True

        customer.refresh_from_db()
        assert customer.full_name == ""
        assert customer.phone.startswith("deleted-")
        assert customer.deleted_at is not None

    def test_ledger_survives_deletion(self, me, customer, card, program):
        """
        التعارض المحلول: حق العميل في الحذف مقابل قاعدة «القيود لا
        تُحذف». الهوية تُمحى والقيود تبقى فيظل رصيد التاجر متوازنًا.
        """
        from django.contrib.auth.hashers import make_password

        from apps.ledger.models import LedgerEntry

        before = LedgerEntry.objects.filter(membership=card).count()

        me.post(reverse("me:delete"))
        OtpCode.objects.filter(phone=customer.phone, purpose=OtpCode.PURPOSE_DELETE).update(
            code_hash=make_password("654321")
        )
        me.delete(reverse("me:delete"), {"code": "654321"}, format="json")

        assert LedgerEntry.objects.filter(membership=card).count() == before

    def test_token_stops_working_after_deletion(self, me, customer):
        from django.contrib.auth.hashers import make_password

        me.post(reverse("me:delete"))
        OtpCode.objects.filter(phone=customer.phone, purpose=OtpCode.PURPOSE_DELETE).update(
            code_hash=make_password("654321")
        )
        me.delete(reverse("me:delete"), {"code": "654321"}, format="json")

        assert me.get(reverse("me:cards")).status_code == 401


class TestNearbyStores:
    @pytest.fixture
    def located(self, brand):
        return factories.BranchFactory(
            brand=brand,
            name="فرع المعادي",
            lat=Decimal("29.9600"),
            lng=Decimal("31.2580"),
        )

    def test_finds_close_branch(self, me, located):
        body = me.get(reverse("me:nearby"), {"lat": "29.9610", "lng": "31.2590"}).json()

        assert len(body) == 1
        assert body[0]["branch_name"] == "فرع المعادي"
        assert body[0]["distance_km"] < 1

    def test_excludes_far_branch(self, me, located):
        # الإسكندرية — أبعد من نصف القطر الافتراضي بكثير
        body = me.get(reverse("me:nearby"), {"lat": "31.20", "lng": "29.92"}).json()

        assert body == []

    def test_marks_membership(self, me, located, customer, brand):
        factories.MembershipFactory(customer=customer, brand=brand)

        body = me.get(reverse("me:nearby"), {"lat": "29.9600", "lng": "31.2580"}).json()

        assert body[0]["is_member"] is True

    def test_missing_coordinates_rejected(self, me):
        response = me.get(reverse("me:nearby"))

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "missing_coordinates"

    def test_branch_without_coordinates_skipped(self, me, brand):
        factories.BranchFactory(brand=brand, lat=None, lng=None)

        body = me.get(reverse("me:nearby"), {"lat": "29.96", "lng": "31.25"}).json()

        assert body == []

    def test_inactive_brand_hidden(self, me, brand):
        brand.is_active = False
        brand.save(update_fields=["is_active"])
        factories.BranchFactory(brand=brand, lat=Decimal("29.96"), lng=Decimal("31.258"))

        body = me.get(reverse("me:nearby"), {"lat": "29.96", "lng": "31.258"}).json()

        assert body == []


class TestIsolation:
    def test_cannot_see_another_customer_wallet(self, me, brand, program):
        other = factories.CustomerFactory()
        other_membership = factories.MembershipFactory(customer=other, brand=brand)
        apply_entry(
            membership=other_membership,
            program=program,
            delta=Decimal("999"),
            reason="earn",
        )

        assert me.get(reverse("me:cards")).json() == []
        assert me.get(reverse("me:activity")).json()["count"] == 0

    def test_deleted_customer_excluded_from_lookup(self, customer):
        customer.anonymize()

        assert Customer.objects.filter(pk=customer.pk, deleted_at__isnull=True).exists() is False
        assert customer.deleted_at <= timezone.now()
