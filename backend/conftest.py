"""تثبيتات مشتركة لكل الاختبارات."""

from decimal import Decimal

import pytest

from tests import factories


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
