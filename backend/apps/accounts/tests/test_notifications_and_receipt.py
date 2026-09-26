"""
صندوق إشعارات العميل، وإيصال عمليته.

الخطر في الصندوق أن يعرض ما لم يصل. الحملة التي فشل إرسالها أو
تُخطّيت موجودة في القاعدة كصف كامل، وعرضها يجعل العميل يسأل عن
عرض لم يُعرض عليه — أو أسوأ: يطالب بخصم لم يُمنح له.

والخطر في الإيصال أن يصمت. العميل يفتحه حين يشكّ: «دفعت وما
اتسجّلش ليه؟». فاتورة تحت الحد الأدنى سبب مشروع، وصمت الشاشة
عنه يجعله يظن أن النظام أكل نقاطه — وهي أول خطوة نحو ترك التطبيق.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.services import issue_tokens_for_customer
from apps.campaigns.models import Campaign, MessageJob
from apps.ledger.models import Transaction
from apps.ledger.services import apply_entry
from apps.loyalty.models import Balance, LoyaltyProgram
from tests import factories

pytestmark = pytest.mark.django_db


@pytest.fixture
def client(customer) -> APIClient:
    api = APIClient()
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {issue_tokens_for_customer(customer)['access']}")
    return api


@pytest.fixture
def campaign(brand):
    return Campaign.objects.create(
        brand=brand,
        name="عرض نهاية الأسبوع",
        message_template="خصم ٢٠٪ على كل شيء الجمعة",
        status=Campaign.STATUS_SENT,
    )


def job(campaign, customer, status):
    return MessageJob.objects.create(
        campaign=campaign,
        customer=customer,
        channel=MessageJob._meta.get_field("channel").choices[0][0],
        status=status,
    )


class TestNotificationsShowOnlyWhatArrived:
    def test_a_sent_message_appears(self, client, campaign, customer):
        job(campaign, customer, MessageJob.STATUS_SENT)

        rows = client.get(reverse("me:notifications")).data["results"]

        assert [row["title"] for row in rows] == ["عرض نهاية الأسبوع"]
        assert rows[0]["body"] == "خصم ٢٠٪ على كل شيء الجمعة"

    def test_the_body_is_rendered_not_the_raw_template(self, client, campaign, customer):
        """
        العميل يرى اسمه لا «{name}».

        الرسالة وصلت هاتفه مركَّبة، فعرض القالب الخام في التطبيق
        يجعل نفس الرسالة تبدو معطوبة — ويُقرأ كخلل في المنصة.
        """
        campaign.message_template = "أهلًا {name}، عندك عرض في {brand}"
        campaign.save(update_fields=["message_template"])
        job(campaign, customer, MessageJob.STATUS_SENT)

        body = client.get(reverse("me:notifications")).data["results"][0]["body"]

        assert "{name}" not in body
        assert customer.full_name in body
        assert campaign.brand.name in body

    @pytest.mark.parametrize(
        "status",
        [MessageJob.STATUS_QUEUED, MessageJob.STATUS_FAILED, MessageJob.STATUS_SKIPPED],
    )
    def test_a_message_that_never_arrived_does_not(self, client, campaign, customer, status):
        """
        الصف موجود في القاعدة، والرسالة لم تصل الهاتف.

        عرضها يجعل العميل يطالب بعرض لم يُعرض عليه.
        """
        job(campaign, customer, status)

        assert client.get(reverse("me:notifications")).data["results"] == []

    def test_another_customers_message_never_leaks(self, client, campaign):
        stranger = factories.CustomerFactory()
        job(campaign, stranger, MessageJob.STATUS_DELIVERED)

        assert client.get(reverse("me:notifications")).data["results"] == []

    def test_unread_counts_what_was_not_read(self, client, campaign, customer):
        """«مقروءة» حالة يرسلها المزوّد لا يخمّنها التطبيق."""
        job(campaign, customer, MessageJob.STATUS_READ)
        second = Campaign.objects.create(
            brand=campaign.brand, name="عرض ثانٍ", message_template="نص", status=Campaign.STATUS_SENT
        )
        job(second, customer, MessageJob.STATUS_DELIVERED)

        data = client.get(reverse("me:notifications")).data

        assert data["unread"] == 1

    def test_anonymous_is_refused(self):
        assert APIClient().get(reverse("me:notifications")).status_code == 401


class TestExpiryWarnings:
    def test_a_balance_expiring_within_a_month_is_announced(
        self, client, membership, program, customer
    ):
        apply_entry(membership=membership, program=program, delta=Decimal("200"), reason="earn")
        Balance.objects.filter(membership=membership, program=program).update(
            expires_at=timezone.now() + timedelta(days=10)
        )

        rows = client.get(reverse("me:notifications")).data["results"]

        assert any(row["kind"] == "expiry" for row in rows)

    def test_a_distant_expiry_is_not(self, client, membership, program):
        """تنبيه قبل سنة ليس تنبيهًا — هو ضجيج يُدرَّب العميل على تجاهله."""
        apply_entry(membership=membership, program=program, delta=Decimal("200"), reason="earn")
        Balance.objects.filter(membership=membership, program=program).update(
            expires_at=timezone.now() + timedelta(days=300)
        )

        rows = client.get(reverse("me:notifications")).data["results"]

        assert not any(row["kind"] == "expiry" for row in rows)

    def test_a_spent_balance_stops_warning(self, client, membership, program):
        """
        التنبيه يُبنى عند القراءة لا يُخزَّن.

        إشعار محفوظ يقول «ينتهي ٢٠٠ نقطة» بعد أن صُرفت يصير كذبًا
        مخزَّنًا يقرؤه العميل بعد أسبوع.
        """
        apply_entry(membership=membership, program=program, delta=Decimal("200"), reason="earn")
        Balance.objects.filter(membership=membership, program=program).update(
            amount=Decimal("0"), expires_at=timezone.now() + timedelta(days=10)
        )

        rows = client.get(reverse("me:notifications")).data["results"]

        assert not any(row["kind"] == "expiry" for row in rows)


class TestTheReceipt:
    def test_it_shows_what_proves_the_purchase(self, client, customer, terminal, cashier):
        txn = Transaction.objects.create(
            terminal=terminal,
            customer=customer,
            staff_user=cashier,
            invoice_no="INV-2291",
            invoice_amount=Decimal("65"),
            status=Transaction.STATUS_CONFIRMED,
            confirmed_at=timezone.now(),
        )

        data = client.get(reverse("me:transaction", args=[txn.id])).data

        assert data["invoice_no"] == "INV-2291"
        assert data["invoice_amount"] == "65.00"
        assert data["branch_name"] == terminal.branch.name
        assert data["cashier_name"] == cashier.user.full_name

    def test_it_shows_the_entry_the_purchase_produced(
        self, client, customer, terminal, membership, program
    ):
        txn = Transaction.objects.create(
            terminal=terminal,
            customer=customer,
            invoice_no="INV-1",
            invoice_amount=Decimal("100"),
            status=Transaction.STATUS_CONFIRMED,
        )
        apply_entry(
            membership=membership,
            program=program,
            delta=Decimal("100"),
            reason="earn",
            transaction_obj=txn,
        )

        data = client.get(reverse("me:transaction", args=[txn.id])).data

        assert len(data["entries"]) == 1
        assert data["entries"][0]["delta"] == "100.00"
        assert data["entries"][0]["balance_after"] == "100.00"
        assert data["nothing_earned_reason"] is None

    def test_a_receipt_of_another_customer_is_not_found(self, client, terminal):
        stranger = factories.CustomerFactory()
        txn = Transaction.objects.create(
            terminal=terminal,
            customer=stranger,
            invoice_no="INV-X",
            invoice_amount=Decimal("100"),
            status=Transaction.STATUS_CONFIRMED,
        )

        assert client.get(reverse("me:transaction", args=[txn.id])).status_code == 404


class TestWhyNothingWasEarned:
    def test_below_the_minimum_says_the_minimum(self, client, customer, terminal, brand, program):
        """
        السبب يُقرأ من القاعدة لا يُخمَّن.

        العميل يستحق السبب نفسه الذي طبّقه المحرك، بالرقم.
        """
        program.rule.min_invoice = Decimal("80")
        program.rule.save(update_fields=["min_invoice"])
        txn = Transaction.objects.create(
            terminal=terminal,
            customer=customer,
            invoice_no="INV-SMALL",
            invoice_amount=Decimal("45"),
            status=Transaction.STATUS_CONFIRMED,
        )

        reason = client.get(reverse("me:transaction", args=[txn.id])).data["nothing_earned_reason"]

        assert "80" in reason
        assert "45" in reason

    def test_a_gifts_only_brand_explains_its_model(self, client, customer, brand, terminal):
        """
        نموذج الهدايا يمنح بمناسبة لا بفاتورة.

        بلا هذا السطر يبدو المتجر معطّلًا لكل من يشتري منه.
        """
        LoyaltyProgram.objects.filter(brand=brand).delete()
        gifts = factories.LoyaltyProgramFactory(brand=brand, type=LoyaltyProgram.TYPE_GIFTS)
        factories.ProgramRuleFactory(program=gifts, min_invoice=Decimal("0"))
        txn = Transaction.objects.create(
            terminal=terminal,
            customer=customer,
            invoice_no="INV-GIFT",
            invoice_amount=Decimal("500"),
            status=Transaction.STATUS_CONFIRMED,
        )

        reason = client.get(reverse("me:transaction", args=[txn.id])).data["nothing_earned_reason"]

        assert "هدايا" in reason

    def test_a_brand_with_no_programme_says_so(self, client, customer, brand, terminal):
        LoyaltyProgram.objects.filter(brand=brand).delete()
        txn = Transaction.objects.create(
            terminal=terminal,
            customer=customer,
            invoice_no="INV-NONE",
            invoice_amount=Decimal("500"),
            status=Transaction.STATUS_CONFIRMED,
        )

        reason = client.get(reverse("me:transaction", args=[txn.id])).data["nothing_earned_reason"]

        assert "برنامج" in reason
