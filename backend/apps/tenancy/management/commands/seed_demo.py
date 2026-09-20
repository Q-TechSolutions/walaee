"""
بيانات بذرة للتطوير.

تبني مؤسسة كاملة بفروعها وبرامجها وعملائها وعملياتها، فيرى المطوّر
نظامًا يعمل من أول دقيقة بدل جداول فارغة.

الاستخدام:  python manage.py seed_demo
            python manage.py seed_demo --reset
"""

from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import Customer
from apps.ledger.models import LedgerEntry, Redemption, Transaction
from apps.loyalty.models import (
    Balance,
    LoyaltyProgram,
    Membership,
    ProgramRule,
    Reward,
)
from apps.pos import codes, services
from apps.tenancy.models import Branch, Brand, Organization, StaffUser, Terminal

User = get_user_model()

# كلمة مرور تطوير فقط. الأمر لا يعمل إلا على قاعدة تطوير — راجع
# الحارس في handle() — وبيانات البذرة لا تُنشأ في الإنتاج إطلاقًا.
DEMO_PASSWORD = "walaee123"  # noqa: S105


class Command(BaseCommand):
    help = "يملأ قاعدة البيانات ببيانات تجريبية للتطوير"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="يمسح البيانات التجريبية السابقة قبل الإنشاء",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="تجاوز حارس الإنتاج — استخدمه بحذر شديد",
        )

    def handle(self, *args, **options):
        # حارس: بيانات بذرة بكلمة مرور معروفة في الإنتاج = باب خلفي
        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "seed_demo لا يعمل خارج التطوير. استخدم --force إن كنت "
                "متأكدًا أن هذه ليست قاعدة إنتاج."
            )

        if options["reset"]:
            self._reset()

        with transaction.atomic():
            org, brand, branches = self._create_tenancy()
            programs = self._create_programs(brand)
            staff = self._create_staff(branches)
            customers = self._create_customers()

        # العمليات خارج المعاملة: كل واحدة تفتح معاملتها الخاصة داخل
        # محرك القيود، ولفّها بمعاملة أكبر يخفي أي خلل في القفل
        self._create_transactions(branches[0], staff["cashier"], customers, programs)

        self._report(brand, staff, customers)

    # ── التنظيم ────────────────────────────────────────────

    def _create_tenancy(self):
        org, _ = Organization.objects.get_or_create(
            name="مجموعة النخبة للمقاهي",
            defaults={
                "legal_name": "شركة النخبة للتجارة والتوزيع",
                "billing_email": "billing@nokhba.example",
            },
        )

        brand, _ = Brand.objects.get_or_create(
            slug="nokhba-cafe",
            defaults={
                "organization": org,
                "name": "نخبة كافيه",
                "category": "cafe",
                "primary_color": "#1F6F5C",
            },
        )

        branches = []
        for name, address, lat, lng in [
            ("الفرع الرئيسي — المعادي", "شارع ٩، المعادي", "29.960", "31.258"),
            ("فرع مدينة نصر", "عباس العقاد، مدينة نصر", "30.060", "31.340"),
        ]:
            branch, _ = Branch.objects.get_or_create(
                brand=brand,
                name=name,
                defaults={"address": address, "lat": Decimal(lat), "lng": Decimal(lng)},
            )
            for label in ("كاشير ١", "كاشير ٢"):
                Terminal.objects.get_or_create(branch=branch, label=label)
            branches.append(branch)

        return org, brand, branches

    # ── البرامج ────────────────────────────────────────────

    def _create_programs(self, brand):
        programs = {}

        points, _ = LoyaltyProgram.objects.get_or_create(
            brand=brand,
            type=LoyaltyProgram.TYPE_POINTS,
            defaults={"name": "نقاط نخبة"},
        )
        ProgramRule.objects.get_or_create(
            program=points,
            defaults={
                "earn_rate": Decimal("1"),
                "min_invoice": Decimal("25"),
                "max_per_day": Decimal("1000"),
                "expiry_months": 12,
                "welcome_bonus": 50,
            },
        )
        programs["points"] = points

        stamps, _ = LoyaltyProgram.objects.get_or_create(
            brand=brand,
            type=LoyaltyProgram.TYPE_STAMPS,
            defaults={"name": "اشترِ ٩ واحصل على العاشرة"},
        )
        ProgramRule.objects.get_or_create(
            program=stamps,
            defaults={
                "earn_rate": Decimal("1"),
                "min_invoice": Decimal("40"),
                "expiry_months": 6,
            },
        )
        programs["stamps"] = stamps

        for title, cost, merchant_cost, stock in [
            ("قهوة مجانية", Decimal("100"), Decimal("18"), None),
            ("خصم ٥٠ جنيهًا", Decimal("450"), Decimal("50"), None),
            ("كيك الشوكولاتة", Decimal("300"), Decimal("35"), 20),
        ]:
            Reward.objects.get_or_create(
                program=points,
                title=title,
                defaults={
                    "cost_amount": cost,
                    "merchant_cost": merchant_cost,
                    "stock": stock,
                },
            )

        Reward.objects.get_or_create(
            program=stamps,
            title="المشروب العاشر مجانًا",
            defaults={
                "cost_amount": Decimal("9"),
                "cost_unit": Reward.UNIT_STAMPS,
                "merchant_cost": Decimal("18"),
            },
        )

        return programs

    # ── الموظفون ───────────────────────────────────────────

    def _create_staff(self, branches):
        staff = {}
        for key, phone, name, role, branch in [
            ("owner", "01000000001", "أحمد المالك", StaffUser.ROLE_OWNER, branches[0]),
            ("manager", "01000000002", "منى المديرة", StaffUser.ROLE_MANAGER, branches[0]),
            ("cashier", "01000000003", "كريم الكاشير", StaffUser.ROLE_CASHIER, branches[0]),
            ("cashier2", "01000000004", "هدى الكاشير", StaffUser.ROLE_CASHIER, branches[1]),
        ]:
            user = User.objects.filter(phone__endswith=phone[1:]).first()
            if user is None:
                user = User.objects.create_user(phone=phone, password=DEMO_PASSWORD, full_name=name)
            record, _ = StaffUser.objects.get_or_create(
                user=user, branch=branch, defaults={"role": role}
            )
            staff[key] = record

        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser(
                phone="01000000000", password=DEMO_PASSWORD, full_name="مدير المنصة"
            )

        return staff

    # ── العملاء ────────────────────────────────────────────

    def _create_customers(self):
        customers = []
        for phone, name in [
            ("01111111111", "سارة عبد الله"),
            ("01222222222", "محمود حسن"),
            ("01333333333", "نورهان سعيد"),
        ]:
            customer, _ = Customer.objects.get_or_create(phone=phone, defaults={"full_name": name})
            customers.append(customer)
        return customers

    # ── عمليات حقيقية عبر المسار الكامل ────────────────────

    def _create_transactions(self, branch, cashier, customers, programs):
        """
        تمر عبر نفس مسار الإنتاج لا بإدخال مباشر في الجداول.

        إدخال قيود يدويًا كان سيملأ الشاشات ببيانات لم تعبر محرك
        القيود، فتبدو سليمة وهي غير قابلة للتفسير.
        """
        terminal = branch.terminals.first()
        amounts = [Decimal("120"), Decimal("85"), Decimal("240"), Decimal("60")]

        for index, amount in enumerate(amounts, start=1):
            customer = customers[index % len(customers)]
            invoice_no = f"SEED-{index:04d}"

            if Transaction.objects.filter(terminal=terminal, invoice_no=invoice_no).exists():
                continue

            code = codes.issue_code(terminal.id)
            txn = services.create_transaction(
                code=code,
                customer=customer,
                invoice_amount=amount,
                invoice_no=invoice_no,
            )
            services.confirm_transaction(txn.id, staff_user=cashier)

    # ── التقرير ────────────────────────────────────────────

    def _report(self, brand, staff, customers):
        out = self.stdout
        ok = self.style.SUCCESS

        out.write("")
        out.write(ok("✓ البيانات التجريبية جاهزة"))
        out.write("")
        out.write(f"  العلامة      {brand.name}")
        out.write(f"  الفروع       {brand.branches.count()}")
        out.write(f"  نقاط البيع   {Terminal.objects.count()}")
        out.write(f"  البرامج      {LoyaltyProgram.objects.count()}")
        out.write(f"  المكافآت     {Reward.objects.count()}")
        out.write(f"  العملاء      {len(customers)}")
        out.write(f"  العمليات     {Transaction.objects.count()}")
        out.write(f"  القيود       {LedgerEntry.objects.count()}")
        out.write("")
        out.write("  حسابات الدخول — كلمة المرور: " + DEMO_PASSWORD)
        out.write("    مدير المنصة   +201000000000")
        out.write("    مالك العلامة  +201000000001")
        out.write("    مدير الفرع    +201000000002")
        out.write("    كاشير         +201000000003")
        out.write("")
        out.write("  عملاء التطبيق (الدخول بـ OTP — الكود يُطبع في سجل الخادم):")
        for customer in customers:
            out.write(f"    {customer.phone}  {customer.full_name}")
        out.write("")

    # ── التنظيف ────────────────────────────────────────────

    def _reset(self):
        """
        يمسح البيانات التجريبية.

        الترتيب يتبع اتجاه المفاتيح الخارجية عكسيًا، و LedgerEntry
        يُحذف بـ queryset لأن الحذف على مستوى السجل ممنوع بالتصميم.
        """
        Redemption.objects.all().delete()
        LedgerEntry.objects.all().delete()
        Transaction.objects.all().delete()
        Balance.objects.all().delete()
        Membership.objects.all().delete()
        Reward.objects.all().delete()
        ProgramRule.objects.all().delete()
        LoyaltyProgram.objects.all().delete()
        StaffUser.objects.all().delete()
        Terminal.objects.all().delete()
        Branch.objects.all().delete()
        Brand.objects.all().delete()
        Organization.objects.all().delete()
        Customer.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        self.stdout.write(self.style.WARNING("✗ مُسحت البيانات التجريبية السابقة"))
