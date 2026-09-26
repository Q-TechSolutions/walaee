"""
تهيئة أول نشر — لا بيانات تجريبية.

`seed_demo` يملأ النظام بمتجر وهمي وكلمة مرور معروفة، وهو ممنوع
في الإنتاج. هذا الأمر يُنشئ الحد الأدنى الحقيقي: حساب فريق المنصة،
وأول مؤسسة بعلامتها وفرعها ونقطة بيعها ومالكها.

    python manage.py bootstrap_platform \\
        --admin-phone 01000000000 \\
        --org "مجموعة النخبة" --brand "نخبة كافيه" \\
        --owner-phone 01011111111

كلمات المرور تُولَّد عشوائيًا وتُطبع مرة واحدة: كلمة مرور في سطر
أوامر تعيش في تاريخ الصدفة إلى الأبد.
"""

import secrets
import string

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from apps.billing.models import Plan, Subscription
from apps.billing.services import get_subscription
from apps.loyalty.models import LoyaltyProgram, ProgramRule
from apps.tenancy.models import Branch, Brand, Organization, StaffUser, Terminal
from apps.tenancy.palette import brand_color

User = get_user_model()

ALPHABET = string.ascii_letters + string.digits


def _password(length: int = 16) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


class Command(BaseCommand):
    help = "يهيّئ أول نشر: حساب المنصة وأول مؤسسة"

    def add_arguments(self, parser):
        parser.add_argument("--admin-phone", required=True, help="هاتف فريق المنصة")
        parser.add_argument("--admin-name", default="فريق ولائي")
        parser.add_argument("--org", help="اسم المؤسسة — اتركه لتخطّي إنشائها")
        parser.add_argument("--brand", help="اسم العلامة التجارية")
        parser.add_argument("--branch", default="الفرع الرئيسي")
        parser.add_argument("--owner-phone", help="هاتف مالك المتجر")
        parser.add_argument("--owner-name", default="المالك")
        parser.add_argument(
            "--plan",
            default=Plan.STARTER,
            choices=[choice[0] for choice in Plan.choices],
        )

    @transaction.atomic
    def handle(self, *args, **options):
        credentials = []

        admin = self._platform_admin(options, credentials)
        organization = None

        if options["org"]:
            if not options["brand"] or not options["owner_phone"]:
                raise CommandError("إنشاء مؤسسة يتطلب --brand و --owner-phone")
            organization = self._first_merchant(options, credentials)

        self._report(admin, organization, credentials)

    # ── فريق المنصة ────────────────────────────────────────

    def _platform_admin(self, options, credentials):
        from apps.accounts.validators import normalize_phone

        phone = normalize_phone(options["admin_phone"])
        user = User.objects.filter(phone=phone).first()

        if user is not None:
            # لا يُعاد ضبط كلمة مرور حساب قائم: إعادة تشغيل الأمر
            # بالخطأ كانت ستقطع وصول من يستخدمه الآن
            self.stdout.write(self.style.WARNING(f"الحساب {phone} موجود — تُرك كما هو"))
            if not user.is_platform_admin:
                user.is_platform_admin = True
                user.is_staff = True
                user.save(update_fields=["is_platform_admin", "is_staff"])
            return user

        password = _password()
        user = User.objects.create_superuser(
            phone=phone, password=password, full_name=options["admin_name"]
        )
        user.is_platform_admin = True
        user.save(update_fields=["is_platform_admin"])

        credentials.append(("فريق المنصة", phone, password))
        return user

    # ── أول متجر ───────────────────────────────────────────

    def _first_merchant(self, options, credentials):
        from apps.accounts.validators import normalize_phone

        organization, _ = Organization.objects.get_or_create(name=options["org"])

        slug = slugify(options["brand"], allow_unicode=False) or "brand"
        if not slug.strip("-"):
            # اسم عربي بالكامل يعطي slug فارغًا — يُشتق من المعرّف
            slug = f"brand-{str(organization.id)[:8]}"

        brand, _ = Brand.objects.get_or_create(
            organization=organization,
            name=options["brand"],
            defaults={"slug": slug, "primary_color": brand_color(options["brand"])},
        )
        branch, _ = Branch.objects.get_or_create(brand=brand, name=options["branch"])
        Terminal.objects.get_or_create(branch=branch, label="كاشير ١")

        # برنامج نقاط افتراضي: علامة بلا برنامج لا تمنح شيئًا،
        # والمالك لا يعرف أن عليه إنشاء واحد قبل أول عملية
        program, created = LoyaltyProgram.objects.get_or_create(
            brand=brand,
            type=LoyaltyProgram.TYPE_POINTS,
            defaults={"name": "نقاط " + brand.name},
        )
        if created:
            ProgramRule.objects.create(program=program)

        subscription = get_subscription(organization)
        subscription.plan = options["plan"]
        subscription.status = Subscription.STATUS_ACTIVE
        subscription.save(update_fields=["plan", "status"])

        owner_phone = normalize_phone(options["owner_phone"])
        owner = User.objects.filter(phone=owner_phone).first()

        if owner is None:
            password = _password()
            owner = User.objects.create_user(
                phone=owner_phone, password=password, full_name=options["owner_name"]
            )
            credentials.append(("مالك المتجر", owner_phone, password))

        StaffUser.objects.get_or_create(
            user=owner, branch=branch, defaults={"role": StaffUser.ROLE_OWNER}
        )

        return organization

    # ── التقرير ────────────────────────────────────────────

    def _report(self, admin, organization, credentials):
        out = self.stdout

        out.write("")
        out.write(self.style.SUCCESS("✓ تمّت التهيئة"))
        out.write("")
        out.write(f"  فريق المنصة   {admin.phone}")

        if organization:
            brand = organization.brands.first()
            out.write(f"  المؤسسة       {organization.name}")
            out.write(f"  العلامة       {brand.name if brand else '—'}")
            out.write(f"  الباقة        {organization.subscription.get_plan_display()}")

        if credentials:
            out.write("")
            out.write(self.style.WARNING("  كلمات المرور تُعرض مرة واحدة — احفظها الآن:"))
            for label, phone, password in credentials:
                out.write(f"    {label:<14} {phone}   {password}")
            out.write("")
            out.write("  غيّرها بعد أول دخول من /django-admin/")

        out.write("")
