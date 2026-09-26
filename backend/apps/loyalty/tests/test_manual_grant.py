"""
المنح اليدوي — الطريق الوحيد الذي يكتب في الرصيد بلا فاتورة.

كل قيد آخر في النظام مربوط بعملية شراء لها رقم وقيمة وكاشير.
هذا القيد وحده يُنشَأ بقرار إنسان، ولذلك هو الباب الذي يدخل منه
الاحتيال الداخلي الموصوف في المستند (م-٠٧): كاشير يمنح نفسه، أو
يمنح أصدقاءه، فتتلوث البيانات التي يُفترض أن يُبنى عليها كل شيء.

لذلك تُثبَّت هنا الضوابط الثلاثة قبل السلوك السعيد: من يملك
الصلاحية، وأن السبب مكتوب وغير فارغ، وأن الرقم لا يمرّ بصفر
زائد. ويُثبَّت أن العلامة لا تصل إلى عضوية علامة أخرى — وهو
الخطأ الذي يحوّل خللًا في الصلاحيات إلى تسريب بيانات بين تجّار.
"""

from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.ledger.models import LedgerEntry
from apps.loyalty.models import Balance
from apps.tenancy.models import StaffUser
from tests import factories

pytestmark = pytest.mark.django_db


def api_for(staff) -> APIClient:
    client = APIClient()
    token = RefreshToken.for_user(staff.user).access_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.fixture
def manager(branch):
    return factories.StaffUserFactory(branch=branch, role=StaffUser.ROLE_MANAGER)


@pytest.fixture
def client(manager) -> APIClient:
    return api_for(manager)


def grant(client, membership, program, amount="100", note="تعويض عن عطل في الفرع"):
    return client.post(
        reverse("loyalty:grant"),
        {
            "membership_id": str(membership.id),
            "program_id": str(program.id),
            "amount": amount,
            "note": note,
        },
        format="json",
    )


class TestWhoMayGrant:
    def test_a_cashier_may_not(self, branch, membership, program):
        """
        أول صورة للاحتيال الداخلي: من يقف عند الصندوق يمنح نفسه.

        الكاشير يحتاج فتح شاشته وتأكيد العمليات — ولا يحتاج أبدًا
        أن يكتب في رصيد بلا فاتورة.
        """
        cashier = factories.StaffUserFactory(branch=branch, role=StaffUser.ROLE_CASHIER)

        response = grant(api_for(cashier), membership, program)

        assert response.status_code == 403
        assert not LedgerEntry.objects.filter(reason=LedgerEntry.REASON_ADJUST).exists()

    def test_a_manager_may(self, client, membership, program):
        assert grant(client, membership, program).status_code == 201

    def test_a_customer_token_may_not(self, customer, membership, program):
        """توكن عميل على مسار تاجر — لا يمنح العميل نفسه نقاطًا."""
        from apps.accounts.services import issue_tokens_for_customer

        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {issue_tokens_for_customer(customer)['access']}"
        )

        assert grant(client, membership, program).status_code == 403


class TestBrandIsolation:
    def test_it_refuses_a_membership_of_another_brand(self, client, program):
        """
        خلل في الصلاحيات هنا لا يعني رقمًا خاطئًا بل تسريبًا: تاجر
        يكتب في محفظة عميل تاجر آخر، ويقرأ اسمه من رسالة الخطأ.
        """
        stranger = factories.MembershipFactory()

        response = grant(client, stranger, program)

        assert response.status_code == 404

    def test_it_refuses_a_programme_of_another_brand(self, client, membership):
        other = factories.LoyaltyProgramFactory()
        factories.ProgramRuleFactory(program=other)

        response = grant(client, membership, other)

        assert response.status_code == 404


class TestTheWrittenReason:
    def test_an_empty_reason_is_refused(self, client, membership, program):
        response = grant(client, membership, program, note="")

        assert response.status_code == 400
        assert "note" in response.data["error"]["details"]

    def test_a_one_word_reason_is_refused(self, client, membership, program):
        """
        «تصحيح» لا يفسّر شيئًا بعد شهر.

        السبب يُقرأ مرتين: مرة في سجل العميل حين يسأل «النقاط دي
        جت منين؟»، ومرة في سجل التدقيق حين يُراجَع المنح.
        """
        assert grant(client, membership, program, note="خطأ").status_code == 400

    def test_the_reason_is_written_on_the_entry(self, client, membership, program):
        grant(client, membership, program, note="هدية عيد ميلاد العميل")

        entry = LedgerEntry.objects.get(reason=LedgerEntry.REASON_ADJUST)
        assert entry.note == "هدية عيد ميلاد العميل"

    def test_it_lands_in_the_audit_log(self, client, manager, membership, program):
        from apps.audit.models import AuditLog

        grant(client, membership, program, note="تعويض عن طلب تأخر")

        log = AuditLog.objects.filter(action="ledger.adjust").latest("created_at")
        assert log.after["note"] == "تعويض عن طلب تأخر"
        assert str(manager.user) in log.actor_label


class TestTheAmount:
    def test_zero_is_refused(self, client, membership, program):
        assert grant(client, membership, program, amount="0").status_code == 400

    def test_a_typo_above_the_ceiling_is_refused(self, client, membership, program):
        """
        السقف يلتقط الصفر الزائد لا سوء النية.

        «٥٠٠» تصير «٥٠٠٠» بضغطة، وتصير التزامًا ماليًا على التاجر
        لا يكتشفه إلا في تقرير الالتزام القائم بعد شهر.
        """
        assert grant(client, membership, program, amount="1000000").status_code == 400

    def test_it_grants_and_moves_the_balance(self, client, membership, program):
        response = grant(client, membership, program, amount="250")

        balance = Balance.objects.get(membership=membership, program=program)
        assert balance.amount == Decimal("250")
        assert response.data["balance_after"] == "250.00"
        assert response.data["unit_label"] == program.unit_label

    def test_a_negative_amount_deducts(self, client, membership, program):
        """
        الخصم اليدوي بنفس المسار وبنفس الضوابط.

        تصحيح خطأ كاشير يحتاج صلاحية وسببًا مكتوبًا تمامًا كالمنح —
        ومسارٌ ثانٍ له كان يعني ضابطين يجب أن يبقيا متطابقين.
        """
        grant(client, membership, program, amount="300")

        grant(client, membership, program, amount="-120", note="عكس منح مكرر بالخطأ")

        assert Balance.objects.get(membership=membership, program=program).amount == Decimal("180")

    def test_it_will_not_push_the_balance_below_zero(self, client, membership, program):
        """
        الرصيد السالب مستحيل منطقيًا — والحارس في المحرك لا هنا.

        ٤٢٢ لا ٤٠٠: الطلب سليم شكلًا ومرفوض بقاعدة عمل، وهو تمييز
        يعتمد عليه العميل ليعرف هل يصحّح مدخلاته أم يفهم قاعدة.
        """
        grant(client, membership, program, amount="50")

        response = grant(client, membership, program, amount="-500", note="خصم أكبر من الرصيد")

        assert response.status_code == 422
        assert Balance.objects.get(membership=membership, program=program).amount == Decimal("50")


class TestTheGiftsModel:
    def test_a_gifts_programme_can_finally_grant(self, client, brand, customer):
        """
        هذا هو سبب وجود المسار.

        `compute_delta` تُرجع صفرًا لنموذج الهدايا عمدًا — الهدية
        تُمنح بمناسبة لا بفاتورة. وبلا هذا المسار كان التاجر الذي
        يختار النموذج يخرج ببرنامج لا يمنح شيئًا أبدًا، وهو أحد
        النماذج الستة المعلنة في صفحة البيع.
        """
        from apps.loyalty.models import LoyaltyProgram

        gifts = factories.LoyaltyProgramFactory(brand=brand, type=LoyaltyProgram.TYPE_GIFTS)
        factories.ProgramRuleFactory(program=gifts)
        membership = factories.MembershipFactory(brand=brand, customer=customer)

        response = grant(client, membership, gifts, amount="1", note="هدية عيد ميلاد")

        assert response.status_code == 201
        assert Balance.objects.get(membership=membership, program=gifts).amount == Decimal("1")
