"""
مصانع بيانات الاختبار.

مشتركة بين كل التطبيقات لأن معظم الاختبارات تحتاج الشجرة كاملة
(مؤسسة ← علامة ← فرع ← طرفية ← كاشير) قبل أن تصل إلى ما تختبره.
"""

from decimal import Decimal

import factory
from django.contrib.auth import get_user_model

from apps.accounts.models import Customer
from apps.loyalty.models import LoyaltyProgram, Membership, ProgramRule, Reward
from apps.tenancy.models import Branch, Brand, Organization, StaffUser, Terminal

User = get_user_model()


class OrganizationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Organization

    name = factory.Sequence(lambda n: f"مؤسسة {n}")
    billing_email = factory.Sequence(lambda n: f"org{n}@example.com")


class BrandFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Brand

    organization = factory.SubFactory(OrganizationFactory)
    name = factory.Sequence(lambda n: f"علامة {n}")
    slug = factory.Sequence(lambda n: f"brand-{n}")
    category = "cafe"


class BranchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Branch

    brand = factory.SubFactory(BrandFactory)
    name = factory.Sequence(lambda n: f"فرع {n}")


class TerminalFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Terminal

    branch = factory.SubFactory(BranchFactory)
    label = factory.Sequence(lambda n: f"كاشير {n}")


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    phone = factory.Sequence(lambda n: f"+2010000{n:05d}")
    full_name = factory.Sequence(lambda n: f"موظف {n}")


class StaffUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StaffUser

    user = factory.SubFactory(UserFactory)
    branch = factory.SubFactory(BranchFactory)
    role = StaffUser.ROLE_CASHIER


class CustomerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Customer

    phone = factory.Sequence(lambda n: f"+2011000{n:05d}")
    full_name = factory.Sequence(lambda n: f"عميل {n}")


class LoyaltyProgramFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LoyaltyProgram

    brand = factory.SubFactory(BrandFactory)
    type = LoyaltyProgram.TYPE_POINTS
    name = factory.Sequence(lambda n: f"برنامج {n}")


class ProgramRuleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProgramRule

    program = factory.SubFactory(LoyaltyProgramFactory)
    earn_rate = Decimal("1")
    min_invoice = Decimal("0")
    max_per_day = None
    expiry_months = 12
    welcome_bonus = 0


class MembershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Membership

    customer = factory.SubFactory(CustomerFactory)
    brand = factory.SubFactory(BrandFactory)


class RewardFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Reward

    program = factory.SubFactory(LoyaltyProgramFactory)
    title = factory.Sequence(lambda n: f"مكافأة {n}")
    cost_amount = Decimal("100")
    merchant_cost = Decimal("20")
    stock = None
