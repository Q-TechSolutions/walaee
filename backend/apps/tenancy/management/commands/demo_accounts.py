"""
حسابات تجربة كاملة — خمسة أدوار جاهزة للعرض.

يُشغَّل على نشر تجريبي لا على إنتاج حقيقي. الفرق بينه وبين
`seed_demo`: هذا ينشئ **حسابات** بكلمات مرور معروفة وأرقام تجربة
تقبل كودًا ثابتًا، ويعمل فوق مؤسسة قائمة أنشأها `bootstrap_platform`.

    python manage.py demo_accounts
    python manage.py demo_accounts --with-data    # مع عمليات وأرصدة

يطبع في النهاية جدول الدخول كاملًا، ويذكّر بالمتغيرات التي يجب
ضبطها ليعمل دخول العميل.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from apps.accounts.models import Customer
from apps.accounts.validators import normalize_phone
from apps.billing.models import MessageCredit, Subscription
from apps.billing.services import apply_credit, get_subscription
from apps.loyalty.models import LoyaltyProgram, ProgramRule, Reward
from apps.tenancy.models import Branch, Brand, StaffUser, Terminal

User = get_user_model()

DEMO_PASSWORD = "Walaee@2026"  # noqa: S105 - حساب عرض بكلمة مرور معلنة عمدًا
DEMO_CODE = "123456"

STAFF = [
    ("01000000000", "مدير المنصة", None, True),
    ("01000000001", "أحمد المالك", StaffUser.ROLE_OWNER, False),
    ("01000000002", "منى المديرة", StaffUser.ROLE_MANAGER, False),
    ("01000000003", "كريم الكاشير", StaffUser.ROLE_CASHIER, False),
]

CUSTOMERS = [
    ("01111111111", "سارة عبد الله", True),
    ("01222222222", "محمود حسن", False),
    ("01333333333", "نورهان سعيد", True),
]


class Command(BaseCommand):
    help = "ينشئ حسابات تجربة لكل الأدوار على مؤسسة قائمة"

    def add_arguments(self, parser):
        parser.add_argument(
            "--with-data",
            action="store_true",
            help="ينشئ مكافآت وعمليات وأرصدة ليكون العرض غير فارغ",
        )
        parser.add_argument("--password", default=DEMO_PASSWORD, help="كلمة مرور موظفي التجربة")
        parser.add_argument(
            "--brand-slug",
            help=("سلاگ العلامة التي يُربَط بها موظفو التجربة. " "الافتراضي: أوسع علامة فروعًا."),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        brand = self._brand(options.get("brand_slug"))

        branch = Branch.objects.filter(brand=brand).order_by("created_at").first()
        if branch is None:
            branch = Branch.objects.create(brand=brand, name="الفرع الرئيسي")

        if not Terminal.objects.filter(branch=branch).exists():
            Terminal.objects.create(branch=branch, label="كاشير ١")

        password = options["password"]
        staff = self._staff(branch, password)
        customers = self._customers()
        self._subscription(brand)

        if options["with_data"]:
            self._data(brand, branch, staff, customers)

        self._report(brand, password)

    def _brand(self, slug: str | None) -> Brand:
        """
        العلامة التي يديرها موظفو التجربة.

        الأوسع فروعًا لا الأقدم إنشاءً: من يفتح لوحة التاجر ليجرّبها
        يجب أن يجد فروعًا وموظفين وأرقامًا. علامة بفرع واحد تجعل نصف
        شاشات اللوحة فارغة، فيستنتج المجرِّب أن الميزة غير موجودة لا
        أن البيانات قليلة.
        """
        if slug:
            brand = Brand.objects.filter(slug=slug).first()
            if brand is None:
                raise CommandError(f"لا توجد علامة بالسلاگ {slug}")
            return brand

        brand = (
            Brand.objects.annotate(reach=Count("branches")).order_by("-reach", "created_at").first()
        )
        if brand is None:
            raise CommandError("لا توجد علامة تجارية. شغّل seed_network أو bootstrap_platform أولًا.")
        return brand

    # ── الموظفون ───────────────────────────────────────────

    def _staff(self, branch, password) -> dict:
        created = {}

        for phone, name, role, is_platform in STAFF:
            normalized = normalize_phone(phone)
            user = User.objects.filter(phone=normalized).first()

            if user is None:
                user = User.objects.create_user(phone=normalized, password=password, full_name=name)
            else:
                # كلمة المرور تُعاد ضبطها هنا عمدًا: هذه حسابات عرض
                # ووجودها بكلمة مرور منسية يجعلها بلا فائدة
                user.set_password(password)
                user.full_name = name
                user.save(update_fields=["password", "full_name"])

            if is_platform:
                user.is_platform_admin = True
                user.is_staff = True
                user.is_superuser = True
                user.save(update_fields=["is_platform_admin", "is_staff", "is_superuser"])
                created["platform"] = user
                continue

            record, _ = StaffUser.objects.get_or_create(
                user=user, branch=branch, defaults={"role": role}
            )
            if record.role != role or not record.is_active:
                record.role = role
                record.is_active = True
                record.save(update_fields=["role", "is_active", "updated_at"])

            created[role] = record

        return created

    # ── العملاء ────────────────────────────────────────────

    def _customers(self) -> list[Customer]:
        result = []

        for phone, name, has_push in CUSTOMERS:
            normalized = normalize_phone(phone)
            customer, _ = Customer.objects.get_or_create(
                phone=normalized, defaults={"full_name": name}
            )

            # الموافقة مسجّلة: بدونها لا يدخل العميل أي شريحة حملة
            # فتبدو كل شاشات الحملات فارغة بلا سبب ظاهر
            customer.full_name = name
            customer.consent_at = customer.consent_at or timezone.now()
            customer.consent_version = customer.consent_version or "v1"
            customer.push_subscription = (
                {"endpoint": f"https://push.example/{normalized}"} if has_push else None
            )
            customer.deleted_at = None
            customer.save(
                update_fields=[
                    "full_name",
                    "consent_at",
                    "consent_version",
                    "push_subscription",
                    "deleted_at",
                    "updated_at",
                ]
            )
            result.append(customer)

        return result

    # ── الاشتراك ───────────────────────────────────────────

    def _subscription(self, brand):
        from apps.billing.models import PLAN_LIMITS
        from apps.tenancy.management.commands.seed_network import plan_for

        organization = brand.organization
        subscription = get_subscription(organization)

        # الباقة تتّسع لفروع العلامة فعلًا لا باقة ثابتة.
        # تثبيتها على «نمو» كان يضع علامة بسبعة عشر فرعًا على باقة
        # حدّها خمسة، فتفتح شاشة الاشتراك على شريطين أحمرين وتفشل
        # أول محاولة لإضافة فرع — وهو عطل يبدو في العرض كأنه عطل
        # في المنتج لا في بيانات التجربة.
        plan = plan_for(Branch.objects.filter(brand=brand).count())
        expected_mrr = PLAN_LIMITS[plan]["monthly_price"]

        # الشرط على الإيراد أيضًا لا على الباقة وحدها: اشتراك رُقّي
        # سابقًا بلا ضبط mrr يبقى صفرًا إلى الأبد، فتعرض لوحة المنصة
        # «MRR صفر» على مؤسسة مشتركة فعلًا — رقم خاطئ يقود قرارًا خاطئًا.
        if subscription.plan != plan or subscription.mrr != expected_mrr:
            subscription.plan = plan
            subscription.status = Subscription.STATUS_ACTIVE
            subscription.mrr = expected_mrr
            subscription.save(update_fields=["plan", "status", "mrr"])

        if not MessageCredit.objects.filter(organization=organization).exists():
            apply_credit(
                organization=organization,
                delta=3_000,
                reason=MessageCredit.REASON_MONTHLY,
                note="رصيد حساب تجربة",
            )

    # ── بيانات لتكون الشاشات غير فارغة ─────────────────────

    def _data(self, brand, branch, staff, customers):
        """
        عمليات حقيقية عبر مسار الإنتاج لا إدخالًا مباشرًا.

        إدخال قيود يدويًا يملأ الشاشات ببيانات لم تعبر محرك القيود،
        فتبدو سليمة وهي غير قابلة للتفسير — وتخفي أي عطل فيه.
        """
        from apps.ledger.models import Transaction
        from apps.pos import codes, services

        program = LoyaltyProgram.objects.filter(brand=brand).first()
        if program is None:
            program = LoyaltyProgram.objects.create(
                brand=brand, type=LoyaltyProgram.TYPE_POINTS, name="نقاط " + brand.name
            )
        if not hasattr(program, "rule"):
            ProgramRule.objects.create(program=program, welcome_bonus=50, expiry_months=12)
            program.refresh_from_db()

        for title, cost, merchant_cost, stock in [
            ("قهوة مجانية", Decimal("100"), Decimal("18"), None),
            ("خصم ٥٠ جنيهًا", Decimal("450"), Decimal("50"), None),
            ("كيك الشوكولاتة", Decimal("300"), Decimal("35"), 20),
        ]:
            Reward.objects.get_or_create(
                program=program,
                title=title,
                defaults={
                    "cost_amount": cost,
                    "merchant_cost": merchant_cost,
                    "stock": stock,
                },
            )

        cashier = staff.get(StaffUser.ROLE_CASHIER)
        terminal = Terminal.objects.filter(branch=branch).first()
        if cashier is None or terminal is None:
            return

        amounts = [Decimal("120"), Decimal("85"), Decimal("240"), Decimal("310")]
        for index, amount in enumerate(amounts, start=1):
            invoice_no = f"DEMO-{index:04d}"
            if Transaction.objects.filter(terminal=terminal, invoice_no=invoice_no).exists():
                continue

            customer = customers[index % len(customers)]
            code = codes.issue_code(terminal.id)
            txn = services.create_transaction(
                code=code,
                customer=customer,
                invoice_amount=amount,
                invoice_no=invoice_no,
            )
            services.confirm_transaction(txn.id, staff_user=cashier)

    # ── التقرير ────────────────────────────────────────────

    def _report(self, brand, password):
        out = self.stdout
        ok = self.style.SUCCESS
        warn = self.style.WARNING

        out.write("")
        out.write(ok("✓ حسابات التجربة جاهزة"))
        out.write("")
        out.write(f"  العلامة: {brand.name}")
        out.write("")
        out.write("  ══ لوحة المتجر  /merchant/  و  إدارة المنصة  /admin/ ══")
        out.write(f"  كلمة المرور للجميع: {password}")
        out.write("")
        out.write("    مدير المنصة    01000000000")
        out.write("    مالك المتجر    01000000001")
        out.write("    مدير الفرع     01000000002")
        out.write("    كاشير          01000000003")
        out.write("")
        out.write("  ══ تطبيق العميل  /  ══")
        out.write(f"  كود التحقق الثابت: {DEMO_CODE}")
        out.write("")
        for phone, name, _ in CUSTOMERS:
            out.write(f"    {phone}    {name}")
        out.write("")
        out.write(warn("  ليعمل دخول العميل أضف إلى .env ثم أعد التشغيل:"))
        out.write("")
        out.write("    DEMO_LOGIN_PHONES=" + ",".join(phone for phone, _, _ in CUSTOMERS))
        out.write(f"    DEMO_LOGIN_CODE={DEMO_CODE}")
        out.write("")
        out.write(
            "  الكود الثابت يعمل لهذه الأرقام وحدها. أي رقم آخر يمر\n"
            "  بالمسار الكامل: كود عشوائي يُرسَل عبر القناة المُعدّة."
        )
        out.write("")
