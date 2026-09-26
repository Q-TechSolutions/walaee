"""
اختيار الفرع النشط لموظف يعمل في أكثر من مكان.

الحالة ليست نادرة: مالك يملك مقهى ومخبزًا، ومدير منطقة يشرف على
فرعين، وكاشير ينتقل بين فرعي نفس العلامة. كان الخادم يختار أولهما
أبجديًا ويصمت — فبيانات العلامة الثانية موجودة ولا سبيل إليها من
الواجهة إطلاقًا.

الترويسة **اختيار لا إذن**. أخطر ما في هذه الميزة أن تتحوّل إلى
باب جانبي: من يرسل معرّف فرع لا يملك فيه دورًا يجب ألّا يحصل على
شيء. أكثر اختبارات هذا الملف تثبت ذلك.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.pos.permissions import get_staff_user, staff_roles
from tests import factories

pytestmark = pytest.mark.django_db

HEADER = "HTTP_X_WALAEE_BRANCH"


def client_for(user, branch_id=None) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    if branch_id is not None:
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}",
            **{HEADER: str(branch_id)},
        )
    return client


@pytest.fixture
def two_brands(db):
    """مالك واحد على علامتين — «ألف» قبل «باء» أبجديًا."""
    first = factories.BrandFactory(name="ألف كافيه")
    second = factories.BrandFactory(name="باء ماركت")

    branch_a = factories.BranchFactory(brand=first, name="الفرع الرئيسي")
    branch_b = factories.BranchFactory(brand=second, name="الفرع الرئيسي")

    owner = factories.StaffUserFactory(branch=branch_a, role="owner")
    factories.StaffUserFactory(user=owner.user, branch=branch_b, role="owner")

    return owner.user, branch_a, branch_b


class TestOrderingIsStable:
    def test_roles_sort_by_brand_then_branch(self, two_brands):
        user, branch_a, branch_b = two_brands

        roles = staff_roles(user)

        assert [role.branch_id for role in roles] == [branch_a.id, branch_b.id]

    def test_login_returns_the_same_order_as_the_resolver(self, two_brands, client):
        """
        ترتيبان مختلفان يعنيان لوحةً تُبرز علامة والخادم يجيب عن
        أخرى — واللوحة تبدو صحيحة تمامًا وهي تعرض أرقامًا ليست لها.
        """
        from apps.accounts.services import login_staff

        user, _, _ = two_brands
        user.set_password("Sirr@12345")
        user.save()

        session = login_staff(phone=user.phone, password="Sirr@12345")

        assert [role["branch_id"] for role in session["roles"]] == [
            str(role.branch_id) for role in staff_roles(user)
        ]


class TestHeaderSelectsTheBranch:
    def test_without_a_header_the_first_role_wins(self, two_brands, rf):
        user, branch_a, _ = two_brands
        request = rf.get("/")
        request.user = user

        assert get_staff_user(request).branch_id == branch_a.id

    def test_header_switches_to_the_second_brand(self, two_brands, rf):
        user, _, branch_b = two_brands
        request = rf.get("/", **{HEADER: str(branch_b.id)})
        request.user = user

        assert get_staff_user(request).branch_id == branch_b.id

    def test_reports_follow_the_chosen_brand(self, two_brands):
        """الاختبار الحقيقي: البيانات تتبع الاختيار لا الاسم المعروض."""
        user, branch_a, branch_b = two_brands

        first = client_for(user, branch_a.id).get(reverse("tenancy:brand")).json()
        second = client_for(user, branch_b.id).get(reverse("tenancy:brand")).json()

        assert first["name"] == "ألف كافيه"
        assert second["name"] == "باء ماركت"


class TestHeaderIsNotAnAuthorization:
    """الضمان الأهم: الترويسة لا تمنح وصولًا إلى ما لا يملكه المرسِل."""

    def test_branch_of_another_merchant_is_ignored(self, two_brands):
        user, branch_a, _ = two_brands
        stranger = factories.BranchFactory(brand=factories.BrandFactory(name="علامة غريبة"))

        body = client_for(user, stranger.id).get(reverse("tenancy:brand")).json()

        # يعود إلى دوره الأول لا إلى العلامة المطلوبة
        assert body["name"] == "ألف كافيه"

    def test_garbage_header_does_not_break_the_request(self, two_brands):
        """معرّف غير صالح يجب ألّا يرمي ٥٠٠ — الترويسة مدخل مستخدم."""
        user, _, _ = two_brands

        response = client_for(user, "ليس معرّفًا").get(reverse("tenancy:brand"))

        assert response.status_code == 200

    def test_empty_header_is_treated_as_absent(self, two_brands, rf):
        user, branch_a, _ = two_brands
        request = rf.get("/", **{HEADER: "   "})
        request.user = user

        assert get_staff_user(request).branch_id == branch_a.id

    def test_inactive_role_cannot_be_selected(self, two_brands, rf):
        """موظف أُوقف في فرع لا يعود إليه بإرسال معرّفه."""
        user, branch_a, branch_b = two_brands
        user.staff_roles.filter(branch=branch_b).update(is_active=False)

        request = rf.get("/", **{HEADER: str(branch_b.id)})
        request.user = user

        assert get_staff_user(request).branch_id == branch_a.id

    def test_customer_token_gets_no_staff_role(self, customer, rf):
        """الترويسة لا تحوّل عميلًا إلى موظف."""
        branch = factories.BranchFactory()
        request = rf.get("/", **{HEADER: str(branch.id)})
        request.user = customer

        assert get_staff_user(request) is None
