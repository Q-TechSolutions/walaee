"""تثبيتات مشتركة لكل الاختبارات."""

from decimal import Decimal

import pytest
from django.core.cache import cache

from tests import factories


@pytest.fixture(autouse=True)
def clear_rate_limits():
    """
    الكاش يحمل عدّادات تحديد المعدل ورموز نقاط البيع.

    بلا تنظيفه بين الاختبارات يرث كل اختبار عدّادات سابقه، فيفشل
    اختبار سليم بـ429 لأن اختبارًا آخر استهلك الحد قبله — وهو فشل
    يعتمد على ترتيب التشغيل فيبدو عشوائيًا ويصعب تفسيره.
    """
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def brand(db):
    return factories.BrandFactory()


@pytest.fixture
def branch(brand):
    return factories.BranchFactory(brand=brand)


@pytest.fixture
def terminal(branch):
    return factories.TerminalFactory(branch=branch)


@pytest.fixture
def cashier(branch):
    return factories.StaffUserFactory(branch=branch)


@pytest.fixture
def customer(db):
    return factories.CustomerFactory()


@pytest.fixture
def program(brand):
    """برنامج نقاط بمعدل ١ نقطة لكل جنيه وبلا سقف."""
    prog = factories.LoyaltyProgramFactory(brand=brand)
    factories.ProgramRuleFactory(program=prog, earn_rate=Decimal("1"))
    prog.refresh_from_db()
    return prog


@pytest.fixture
def membership(customer, brand):
    return factories.MembershipFactory(customer=customer, brand=brand)
