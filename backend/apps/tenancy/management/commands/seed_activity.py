"""
تاريخ نشاط بحجم واقعي — ما يجعل الشاشات تقول شيئًا.

`seed_network` يبني الشبكة: علامات وفروع وبرامج ومكافآت. لكن شبكة
بلا نشاط تُنتج لوحة صحيحة وفارغة: كل مخطط خط مستقيم على الصفر، وكل
جدول سطر «لا توجد بيانات»، وكل مؤشر مقارنة يطبع «—» لأن لا فترة
سابقة يُقاس عليها. المنتج يبدو معطوبًا وهو سليم.

هذا الأمر يملأ **الاثني عشر شهرًا الماضية** بعملاء وعمليات وقيود
واستبدالات وحملات، بحجم قاعدة تجارية حقيقية لا بثلاث عمليات.

ما يمرّ به وما يتجاوزه — والسبب:

  • القيود تُكتب بـ `ledger.services.apply_entry` وحده، والمقدار
    يُحسب بـ `loyalty.rules.compute_delta`. أي طريق آخر كان سيولّد
    أرصدة لا يقابلها قيد، فينجح `seed_activity` وتفشل شاشة «تسوية
    دفتر القيود» — أسوأ من قاعدة فارغة.

  • يتجاوز `pos.services.confirm_transaction`. تلك الدالة تنسّق
    عمليةً **حاضرة**: تستهلك رمز QR له عمر دقائق، وتُلزم الكاشير
    بفرعه، وتُجدول إشعارًا للعميل. تاريخ مُعاد بناؤه لا عميل فيه
    ينتظر إشعارًا عن شراء العام الماضي.

  • الطوابع الزمنية تُرجَع للخلف بـ `queryset.update()` بعد الكتابة،
    لأن `apply_entry` يكتب «الآن» ولا يقبل تاريخًا — وهو محقّ في
    ذلك. الإرجاع هذا يخترق حارس append-only، فالأمر يرفض العمل إن
    كانت مصدّات القاعدة في `infra/postgres/02-append-only.sql`
    مثبّتة: هناك تعني قاعدة إنتاج، وبيانات مُختلَقة في إنتاج أسوأ
    من شاشة فارغة بما لا يُقاس.

  • الإرجاع يحدث بعد **كل** قيد لا في النهاية. السقف اليومي في
    `apply_entry` يسأل «كم مُنح اليوم؟»، ولو بقيت قيود سنة كاملة
    مؤرّخة بلحظة التشغيل لرفض السقف أغلبها.

الأرقام ليست عشوائية موحّدة: كل عميل يأخذ **نمط سلوك** (مُخلص،
منتظم، متقطّع، متسرّب). التوزيع الموحّد كان سيجعل «خاملون ٩٠ يومًا»
صفرًا و«نشطون» مئة بالمئة — أرقامًا لا تشبه أي قاعدة عملاء حقيقية،
ولا تُظهر الشرائح التي بُنيت الحملات لاستهدافها.

إعادة التشغيل **تكمّل ولا تضاعف**: العميل يُعرَف برقم هاتف مُشتق من
ترتيبه، ومن له عضوية بالفعل يُتخطّى تاريخه. فتشغيل توقّف في منتصفه
يُستكمَل بتشغيل ثانٍ، ولا يحتاج مسحًا.

    python manage.py seed_activity
    python manage.py seed_activity --scale 0.1     # تشغيل سريع للفحص
    python manage.py seed_activity --only super-el-hayy
"""

from __future__ import annotations

import logging
import random
from datetime import timedelta
from decimal import Decimal
from typing import NamedTuple

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.models import Count, Sum
from django.utils import timezone

from apps.accounts.models import Customer
from apps.billing.models import Invoice, Subscription
from apps.campaigns.models import Campaign, Channel, MessageJob
from apps.fraud import services as fraud
from apps.fraud.models import FraudSignal
from apps.ledger import services as ledger
from apps.ledger.models import LedgerEntry, Redemption, Transaction
from apps.loyalty.models import LoyaltyProgram, Membership, Reward
from apps.loyalty.rules import compute_delta
from apps.tenancy.models import Branch, Brand, StaffUser, Terminal

# ══════════════════════ ثوابت التوليد ══════════════════════

#: بذرة ثابتة. تشغيلان على قاعدتين مختلفتين يعطيان نفس الأرقام،
#: فيمكن التقاط صورة للوحة ومقارنتها بعد أسبوع بلا أن تتغيّر تحتها.
SEED = 20260926

#: نطاق أرقام محفوظ لعملاء هذا الأمر: ‎+2010 5 NN xxxxx.
#:
#: الخامس دائمًا «٥»، ثم رقمان للعلامة وخمسة لترتيب العميل فيها.
#: أرقام التجربة المعلَنة (‎01111111111 وأخواتها) وأرقام الموظفين
#: (‎0100000000x) خارج النطاق، فلا يسحب التوليد رقمًا يدخل به أحد.
PHONE_PREFIX = "+20105"

MONTHS = 12

#: متوسط سلّة الشراء لكل فئة — (الأدنى، الأعلى) بالجنيه.
#:
#: الفئة لا الحد الأدنى في قاعدة البرنامج: `min_invoice` شرط أهلية
#: لا وصف لما يشتريه الناس. مقهى حدّه الأدنى ٢٥ جنيهًا لا يعني أن
#: متوسط فاتورته ٢٥ — يعني أن أقل من ذلك لا يستحق ختمًا.
BASKETS: dict[str, tuple[int, int]] = {
    "مقاهٍ ومشروبات": (45, 165),
    "مخبوزات وحلويات": (40, 230),
    "مطاعم": (130, 680),
    "مشويات": (260, 1150),
    "مأكولات بحرية": (300, 1450),
    "صيدليات": (65, 900),
    "بقالة وسوبر ماركت": (95, 1350),
    "تجميل وعناية": (160, 950),
    "رياضة ولياقة": (300, 1550),
    "ملابس وأحذية": (240, 2300),
    "إلكترونيات": (750, 17000),
    "مكتبات وقرطاسية": (55, 520),
    "هدايا وزهور": (120, 850),
}
BASKET_FALLBACK = (80, 600)


class Archetype(NamedTuple):
    """
    نمط سلوك عميل.

    `share` نصيبه من القاعدة، و`visits_per_month` معدّل زياراته حين
    يكون نشطًا، و`life_months` عدد الأشهر التي يظل فيها كذلك بعد
    انضمامه. المتسرّب ينضم قديمًا ويتوقّف مبكّرًا — وهو وحده ما
    يجعل شريحة «خاملون ٩٠ يومًا» رقمًا حقيقيًا.
    """

    key: str
    share: float
    visits_per_month: tuple[float, float]
    life_months: tuple[int, int]
    basket_factor: float


ARCHETYPES = (
    # المُخلص: أكثر إنفاقًا وأكثر تكرارًا — عليه تُبنى شريحة VIP
    Archetype("loyal", 0.08, (2.0, 3.4), (MONTHS, MONTHS), 1.45),
    Archetype("regular", 0.19, (1.1, 1.9), (MONTHS - 2, MONTHS), 1.10),
    Archetype("casual", 0.30, (0.6, 1.1), (MONTHS - 4, MONTHS), 0.95),
    Archetype("rare", 0.24, (0.22, 0.5), (MONTHS - 5, MONTHS), 0.85),
    # المتسرّب: نشط ثم يصمت. لا يُحاكى بحذف بيانات بل بعمر أقصر
    Archetype("churned", 0.19, (0.9, 1.7), (3, 7), 1.00),
)

#: أسماء مصرية شائعة. التكرار بينها مقصود ومطابق للواقع: قاعدة
#: بأربعة آلاف اسم فريد تمامًا تكشف أنها مُختلَقة من أول نظرة.
FIRST_NAMES = (
    "أحمد محمد محمود مصطفى إسلام كريم عمر يوسف حسن علي إبراهيم خالد طارق "
    "شريف هاني وليد عماد سامح رامي زياد باسم أيمن حاتم مينا بيشوي "
    "سارة منى نورهان دعاء هبة إيمان مريم فاطمة عائشة ياسمين رانيا شيماء "
    "أسماء سلمى حبيبة ملك نادية سمية أميرة داليا ريهام هدير جميلة مارينا "
    "عبد الرحمن عبد الله محمد أمين أم كلثوم"
).split()

LAST_NAMES = (
    "عبد الله السيد حسين شاكر الشربيني عبد العال منصور الدسوقي فتحي رزق "
    "الجندي عويس القاضي الشيمي بدوي غنيم سلامة الفقي زكي عبد الرحيم "
    "النجار الحداد العطار الصعيدي البحيري الدمنهوري الأسيوطي المنياوي "
    "سعد الدين أبو زيد أبو العلا شلبي مرسي قنديل حجازي سرور الطحاوي "
    "عبد الغني نصار الجزار سويلم عرفة خليفة الباز صادق راغب"
).split()

#: قوالب الحملات — ما يرسله تاجر حقيقي لا نصوص «Lorem».
CAMPAIGN_SPECS = (
    ("عرض نهاية الأسبوع", "خاصمك خصم ١٥٪ على طلبك القادم لحد الأحد. {name}، شوفنا!", 0.88, 0.31),
    ("رجعنا نسأل عليك", "{name}، وحشتنا! رصيدك {balance} نقطة لسه مستنيك.", 0.81, 0.19),
    ("مكافأتك قربت", "باقي شوية على مكافأتك الجديدة. {name}، كمّلها!", 0.93, 0.44),
    ("افتتاح فرع جديد", "فرعنا الجديد فتح. {name}، أول زيارة فيها نقاط مضاعفة.", 0.86, 0.26),
    ("كل سنة وأنت طيب", "{name}، عيد ميلاد سعيد! هديتك مستنية في أي فرع.", 0.95, 0.52),
)


class Command(BaseCommand):
    help = "يملأ الاثني عشر شهرًا الماضية بنشاط بحجم واقعي"

    def add_arguments(self, parser):
        parser.add_argument(
            "--scale",
            type=float,
            default=1.0,
            help="معامل الحجم. ٠٫١ للفحص السريع، ١ للحجم الكامل.",
        )
        parser.add_argument(
            "--only",
            action="append",
            default=[],
            metavar="SLUG",
            help="يقصر التوليد على علامات محدّدة. يتكرر.",
        )
        parser.add_argument(
            "--per-branch",
            type=int,
            default=104,
            help="عملاء لكل فرع في العلامة الرئيسية.",
        )

    def handle(self, *args, **options):
        self._guard_append_only()
        self._quiet_engine_logs()

        random.seed(SEED)
        self.scale = max(0.01, float(options["scale"]))
        self.per_branch = options["per_branch"]
        self.now = timezone.now()

        # العدّاد يبدأ بعد ما هو مكتوب، لا من الصفر. `invoice_no`
        # فريد لكل طرفية، وبدء تشغيل ثانٍ من الصفر كان يعيد إنتاج
        # نفس الأرقام فيصطدم بأول فاتورة كتبها التشغيل الأول.
        self.invoice_seq = Transaction.objects.count()

        # مؤسستان تُتركان بفاتورة غير مسدّدة: شاشة التحصيل في
        # لوحة المنصة تُفتح لمتابعة المتأخرين، وقاعدة كلها
        # مسدّدة تجعلها فارغة بلا سبب
        self.unpaid = set(
            Subscription.objects.order_by("created_at").values_list("organization_id", flat=True)[
                :2
            ]
        )

        brands = self._brands(options["only"])
        if not brands:
            raise CommandError("لا توجد علامات. شغّل seed_network أولًا.")

        # ترتيب ثابت للعلامة داخل نطاق الهواتف. `hash()` على نصّ لا
        # يصلح: بايثون يعشوِش بذرته لكل عملية، فتشغيلان يعطيان نطاقين
        # مختلفين ويتضاعف العملاء بلا أن يكتشف أحد السبب.
        self.ordinals = {
            slug: index
            for index, slug in enumerate(
                Brand.objects.order_by("slug").values_list("slug", flat=True)
            )
        }

        primary = brands[0]
        totals = {"customers": 0, "transactions": 0, "entries": 0, "redemptions": 0}

        for brand in brands:
            # العلامة الأوسع هي التي يدخل عليها حساب التجربة، فتأخذ
            # قاعدة كاملة. البقية تأخذ ما يجعل الدليل العام وإحصاءات
            # المنصة حقيقية بلا إطالة زمن التشغيل بلا داعٍ.
            depth = 1.0 if brand.id == primary.id else 0.42
            stats = self._seed_brand(brand, depth=depth)
            for key, value in stats.items():
                totals[key] += value

            reviewed = self._review_signals(brand)
            self.stdout.write(
                f"  {brand.name}: {stats['customers']} عميلًا · "
                f"{stats['transactions']} عملية · {stats['entries']} قيدًا · "
                f"{reviewed} إشارة مُراجَعة"
            )

        self._seed_campaigns(primary)
        invoices = self._seed_billing()
        self.stdout.write(f"  الفوترة: {invoices} فاتورة")

        self.stdout.write(
            self.style.SUCCESS(
                f"\n{totals['customers']} عميلًا · {totals['transactions']} عملية · "
                f"{totals['entries']} قيدًا · {totals['redemptions']} استبدالًا"
            )
        )

    # ═══════════════════════ تاريخ الفوترة ═══════════════════════

    def _seed_billing(self) -> int:
        """
        فواتير الأشهر الماضية لكل اشتراك.

        بدونها تبقى شاشة «الاشتراكات والفواتير» في اللوحتين فارغة
        على منصّة عمرها سنة: البذرة تبني اثني عشر شهرًا من تاريخ
        الولاء ثم تترك دفتر الفوترة بلا سطر واحد. تاجر يفتح
        اشتراكه يرى «لا توجد فواتير بعد» فيستنتج أنه لم يُحاسَب
        قطّ — وفريق المنصة يفتح لوحته فلا يجد ما يراجعه.

        الفواتير تُكتب مباشرةً لا عبر `issue_invoice`: تلك الدالة
        تدفع الاشتراك دورةً إلى الأمام مع كل إصدار، فاستدعاؤها
        اثنتي عشرة مرة كان يقذف تاريخ التجديد إلى سنة قادمة.
        الغرض هنا استعادة ما **مضى** لا محاكاة ما سيأتي.
        """
        issued = 0
        today = self.now.date()

        for subscription in Subscription.objects.select_related("organization"):
            price = Decimal(subscription.limit("monthly_price") or 0)
            if price <= 0:
                # الباقة المجانية لا تُصدَر لها فاتورة أصلًا
                continue

            # يُبدأ من الدورة السابقة للحالية رجوعًا: الدورة الجارية
            # لم تنتهِ بعد، وإصدار فاتورتها الآن يقول للتاجر إنه
            # مدين بشهر لم يستهلكه
            period_end = subscription.current_period_start
            for index in range(MONTHS):
                period_start = period_end - timedelta(days=30)
                if period_start.date() > today:
                    break

                number = f"INV-{period_start:%Y%m}-{str(subscription.organization_id)[:6]}"
                if Invoice.objects.filter(number=number).exists():
                    period_end = period_start
                    continue

                # آخر فاتورتين تبقيان مستحقّتين: لوحة المنصة تعرض
                # «غير مسدّدة» وهي الشاشة التي تُفتح لمتابعة التحصيل،
                # وقاعدة كلها مسدّدة تجعلها فارغة بلا سبب
                overdue = index == 0 and subscription.organization_id in self.unpaid
                status = Invoice.STATUS_ISSUED if overdue else Invoice.STATUS_PAID

                invoice = Invoice.objects.create(
                    subscription=subscription,
                    number=number,
                    amount=price,
                    status=status,
                    period_start=period_start,
                    period_end=period_end,
                    issued_at=period_start,
                )
                # `issued_at` و`created_at` يُكتبان بالتاريخ الماضي
                # صراحةً: الأول حقل عادي والثاني افتراضه «الآن»
                Invoice.objects.filter(pk=invoice.pk).update(
                    created_at=period_start,
                    paid_at=None if overdue else period_end,
                )
                issued += 1
                period_end = period_start

        return issued

    # ═══════════════════════ الحرّاس ═══════════════════════

    def _guard_append_only(self):
        """
        يرفض العمل على قاعدة مُحصّنة بمصدّات append-only.

        وجود المصدّ يعني أن هذه قاعدة عوملت كإنتاج. الفشل هنا بسطر
        واضح أرحم من فشل بعد ألف عملية بخطأ من PostgreSQL لا يشرح
        شيئًا، وأرحم بما لا يُقاس من نجاح يزرع بيانات مُختلَقة في
        دفتر قيود حقيقي.
        """
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pg_trigger WHERE tgname = %s",
                ["ledger_entry_immutable"],
            )
            if cursor.fetchone():
                raise CommandError(
                    "مصدّات append-only مثبّتة على هذه القاعدة — "
                    "seed_activity لا يعمل على قاعدة إنتاج."
                )

    def _quiet_engine_logs(self) -> None:
        """
        يكتم سجلّ المحرّك أثناء البذر.

        `apply_entry` يسجّل سطرًا لكل قيد — وهو صحيح في الإنتاج حيث
        القيد حدث يُدقَّق. هنا يعني عشرات الآلاف من الأسطر تغرق فيها
        حصيلة التشغيل، فلا يرى المشغّل ما إذا نجح الأمر أصلًا.
        """
        for name in ("apps.ledger.services", "apps.fraud.services", "apps.pos.services"):
            logging.getLogger(name).setLevel(logging.WARNING)

    def _brands(self, only: list[str]) -> list[Brand]:
        """العلامات مرتّبة بالاتساع: الأوسع أولًا فهي علامة العرض."""

        query = Brand.objects.annotate(reach=Count("branches")).filter(reach__gt=0)
        if only:
            query = query.filter(slug__in=only)
        return list(query.order_by("-reach", "created_at"))

    # ═══════════════════════ علامة واحدة ═══════════════════════

    def _seed_brand(self, brand: Brand, *, depth: float) -> dict[str, int]:
        program = (
            LoyaltyProgram.objects.filter(brand=brand, is_active=True)
            .select_related("rule")
            .first()
        )
        branches = list(Branch.objects.filter(brand=brand).order_by("created_at"))
        terminals = list(Terminal.objects.filter(branch__brand=brand).select_related("branch"))
        if not terminals:
            return {"customers": 0, "transactions": 0, "entries": 0, "redemptions": 0}

        cashiers = self._cashiers(brand, branches)
        rewards = list(
            Reward.objects.filter(program=program, is_active=True).order_by("cost_amount")
        )
        basket = BASKETS.get(brand.category, BASKET_FALLBACK)

        target = max(1, int(len(branches) * self.per_branch * depth * self.scale))
        stats = {"customers": 0, "transactions": 0, "entries": 0, "redemptions": 0}

        # الفروع ليست متساوية. الأول أقدم وأشهر، فيأخذ نصيبًا أكبر —
        # وبدون هذا التفاوت يظهر تقرير «تفصيل حسب الفرع» بأعمدة
        # متطابقة تمامًا، وهو أول ما يكشف أن البيانات مُختلَقة.
        weights = [max(0.35, 1.6 - 0.11 * index) for index in range(len(terminals))]

        for index in range(target):
            customer = self._customer(brand, index)
            if customer is None:
                continue
            stats["customers"] += 1

            archetype = self._archetype()
            joined = self._join_date(archetype)
            membership, fresh = self._membership(customer, brand, joined)

            # عضوية قائمة = تاريخها مكتوب في تشغيل سابق. توليد زيارات
            # لها ثانيةً كان يضاعف كل رقم في اللوحة مع كل تشغيل.
            if not fresh:
                continue

            visits = self._visit_dates(archetype, joined)
            for order, moment in enumerate(visits):
                terminal = random.choices(terminals, weights=weights, k=1)[0]
                cashier = cashiers.get(terminal.branch_id)
                amount = self._amount(basket, archetype.basket_factor)

                written = self._transaction(
                    terminal=terminal,
                    cashier=cashier,
                    customer=customer,
                    membership=membership,
                    program=program,
                    amount=amount,
                    moment=moment,
                    first_visit=order == 0,
                )
                stats["transactions"] += 1
                stats["entries"] += written

            if rewards and visits:
                stats["redemptions"] += self._redemptions(
                    membership=membership,
                    rewards=rewards,
                    cashier=next(iter(cashiers.values()), None),
                    last_visit=visits[-1],
                )

        return stats

    def _cashiers(self, brand: Brand, branches: list[Branch]) -> dict:
        """كاشير لكل فرع — من موجود، وإلا فبأي موظف في العلامة."""
        by_branch = {}
        staff = list(StaffUser.objects.filter(branch__brand=brand).select_related("user", "branch"))
        for member in staff:
            by_branch.setdefault(member.branch_id, member)

        fallback = staff[0] if staff else None
        for branch in branches:
            by_branch.setdefault(branch.id, fallback)
        return {key: value for key, value in by_branch.items() if value is not None}

    # ═══════════════════════ العميل ═══════════════════════

    def _customer(self, brand: Brand, index: int) -> Customer | None:
        """
        عميل بهاتف مُشتق من ترتيبه، فإعادة التشغيل لا تضاعف القاعدة.

        رقم الهاتف يحمل رقم العلامة أيضًا: عميل واحد قد يكون عضوًا في
        علامتين في الواقع، لكن خلط ذلك في البذرة كان سيجعل «إجمالي
        العملاء» في كل لوحة يعتمد على ترتيب التشغيل.
        """
        ordinal = self.ordinals.get(brand.slug, 99)
        phone = f"{PHONE_PREFIX}{ordinal:02d}{index:05d}"

        existing = Customer.objects.filter(phone=phone).first()
        if existing is not None:
            return existing

        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        # الموافقة ليست شاملة: ‎١٤٪ لا يوافقون على التواصل، وهم من
        # يجعل «المستهدفون» في الحملات أقل من «إجمالي العملاء».
        consented = random.random() > 0.14

        # من ثبّت التطبيق يستقبل إشعارًا مجانيًا. بلا هذه النسبة تمرّ
        # كل حملة على واتساب والرسائل النصية، فتظهر تكلفة أعلى من
        # الحقيقة ويختفي أهمّ ما يميّز المنتج: قناة بلا تكلفة.
        installed = consented and random.random() < 0.42

        return Customer.objects.create(
            phone=phone,
            full_name=name,
            consent_at=self.now - timedelta(days=random.randint(1, 360)) if consented else None,
            consent_version="1.0" if consented else "",
            push_subscription={"endpoint": "seed", "keys": {}} if installed else None,
            last_seen_at=self.now - timedelta(days=random.randint(0, 200)),
        )

    def _archetype(self) -> Archetype:
        return random.choices(ARCHETYPES, weights=[a.share for a in ARCHETYPES], k=1)[0]

    def _join_date(self, archetype: Archetype):
        """
        تاريخ انضمام موزّع على السنة بميل للأشهر الأخيرة.

        الانضمام المتزايد هو ما يجعل «عملاء جدد» موجبًا ومؤشر التغيّر
        ذا معنى. توزيع مسطّح كان سيعطي نموًا صفريًا كل شهر.
        """
        span = min(MONTHS, archetype.life_months[1])

        # الأسّ ١٫٣٥ يميل بالتوزيع نحو الأشهر الأخيرة بلا أن يسحقه
        # عليها: الوسيط يقع قرب الشهر الخامس. ميل أقوى كان يجعل
        # الأغلبية تنضم هذا الأسبوع، فلا يبقى لأحد تاريخ يُعرَض —
        # وهو ما كان يفرّغ كل مخطط سنوي رغم امتلاء قاعدة العملاء.
        weighted = random.random() ** 1.35
        days = int(weighted * span * 30)
        return self.now - timedelta(days=max(1, days))

    def _membership(self, customer: Customer, brand: Brand, joined) -> tuple[Membership, bool]:
        membership, created = Membership.objects.get_or_create(customer=customer, brand=brand)
        if created:
            # joined_at بـ auto_now_add — لا يُمرَّر في الإنشاء
            Membership.objects.filter(pk=membership.pk).update(joined_at=joined, created_at=joined)
            membership.joined_at = joined
        return membership, created

    def _visit_dates(self, archetype: Archetype, joined) -> list:
        """زيارات العميل مرتّبة زمنيًا من انضمامه حتى نهاية عمره النشط."""
        life = random.randint(*archetype.life_months)
        rate = random.uniform(*archetype.visits_per_month)

        active_days = min((self.now - joined).days, life * 30)
        if active_days < 1:
            return []

        count = max(1, int(round(rate * active_days / 30)))
        moments = []
        for _ in range(count):
            offset = random.randint(0, active_days)
            moment = joined + timedelta(
                days=offset,
                hours=random.choice([10, 12, 13, 15, 17, 18, 19, 20, 21, 22]),
                minutes=random.randint(0, 59),
            )
            if moment < self.now:
                moments.append(moment)
        return sorted(moments)

    def _amount(self, basket: tuple[int, int], factor: float) -> Decimal:
        """
        قيمة فاتورة داخل نطاق الفئة، بذيل أعلى قليلًا.

        الفواتير الحقيقية ليست موزّعة توزيعًا موحّدًا: الأغلبية قرب
        الأدنى وقلّة كبيرة تسحب المتوسط. رقم موحّد كان سيجعل «متوسط
        الفاتورة» يساوي منتصف النطاق بالضبط في كل فرع.
        """
        low, high = basket
        skewed = low + (high - low) * random.random() ** 1.7
        value = Decimal(str(round(skewed * factor, 2)))

        # فواتير مستديرة كبيرة تُطلق قاعدة الاحتيال «مبلغ مستدير» —
        # ‎٣٪ منها كافية لتظهر الشاشة بإشارات حقيقية لا مزروعة يدويًا
        if random.random() < 0.03 and value > 200:
            value = (value / 100).quantize(Decimal("1")) * 100
        return max(Decimal("5.00"), value)

    # ═══════════════════════ العملية والقيد ═══════════════════════

    @transaction.atomic
    def _transaction(
        self, *, terminal, cashier, customer, membership, program, amount, moment, first_visit
    ) -> int:
        """
        عملية مؤكّدة مؤرّخة في الماضي، وقيدها إن استحقّت.

        تعود بعدد القيود المكتوبة — صفر مشروع تمامًا: فاتورة دون
        الحد الأدنى أو برنامج هدايا يُمنح يدويًا لا يُنتج قيدًا.
        """
        # عدّاد لا طابع زمني: `invoice_no` فريد لكل طرفية، وفاتورتان
        # في نفس الثانية على نفس الكاشير كانتا ستصطدمان بالقيد.
        self.invoice_seq += 1
        invoice = f"{moment:%y%m}-{self.invoice_seq:06d}"

        txn = Transaction.objects.create(
            terminal=terminal,
            staff_user=cashier,
            customer=customer,
            invoice_no=invoice,
            invoice_amount=amount,
            status=Transaction.STATUS_CONFIRMED,
            confirmed_at=moment,
            created_at=moment,
        )

        written = 0
        rule = getattr(program, "rule", None)
        if rule is not None:
            # مكافأة الانضمام على أول عملية — نفس ترتيب
            # `confirm_transaction`: المكافأة قبل أول منح، فيقرأ
            # العميل في سجلّه «مكافأة انضمام» ثم «نقاط شراء».
            if first_visit:
                welcome = ledger.grant_welcome_bonus(
                    membership=membership, program=program, actor=cashier
                )
                if welcome is not None:
                    self._backdate(welcome, moment)
                    written += 1

            delta = compute_delta(rule, amount)
            if delta > 0:
                written += self._entry(
                    membership=membership,
                    program=program,
                    delta=delta,
                    reason=LedgerEntry.REASON_EARN,
                    txn=txn,
                    actor=cashier,
                    moment=moment,
                )

        # قواعد الشذوذ الحقيقية على العملية الحقيقية. القواعد
        # الزمنية لن تُطلق على ماضٍ بعيد وهذا صحيح: اندفاع كاشير
        # قبل ثمانية أشهر ليس تنبيهًا يُراجَع اليوم.
        #
        # الإشارة تُؤرَّخ بتاريخ عمليتها لا بلحظة البذر: قائمة
        # مراجعة كلها «اليوم» تجعل كل إشارة تبدو عاجلة.
        signals = fraud.evaluate(txn)
        if signals:
            FraudSignal.objects.filter(pk__in=[s.pk for s in signals]).update(created_at=moment)

        return written

    def _entry(self, *, membership, program, delta, reason, txn, actor, moment) -> int:
        try:
            entry = ledger.apply_entry(
                membership=membership,
                program=program,
                delta=delta,
                reason=reason,
                transaction_obj=txn,
                actor=actor,
            )
        except ledger.LedgerError:
            # السقف اليومي أو الرصيد غير الكافي — رفض مشروع من
            # المحرّك، لا خطأ في البذرة. يُتجاوَز بصمت كما في الواقع.
            return 0

        self._backdate(entry, moment)
        return 1

    def _backdate(self, entry: LedgerEntry, moment) -> None:
        """
        يُرجع طابع القيد للخلف — راجع شرح الحارس في أعلى الملف.

        يجري فورًا بعد الكتابة لا في نهاية التشغيل: السقف اليومي
        يقرأ قيود «اليوم»، وتركها كلها في يوم واحد كان سيرفض أغلبها.
        """
        LedgerEntry.objects.filter(pk=entry.pk).update(created_at=moment)

    # ═══════════════════════ الاستبدال ═══════════════════════

    def _redemptions(self, *, membership, rewards, cashier, last_visit) -> int:
        """
        استبدالات مصروفة فعلًا — عبر خدمتي الاستبدال والصرف.

        كتابة `Redemption` مباشرةً كانت ستتركه بلا قيد خصم، فيظهر
        «الالتزام القائم» في اللوحة أعلى من الحقيقة إلى الأبد.
        """
        if cashier is None or random.random() > 0.34:
            return 0

        affordable = [
            reward
            for reward in rewards
            if self._balance_of(membership, reward) >= reward.cost_amount
        ]
        if not affordable:
            return 0

        reward = random.choice(affordable)
        moment = last_visit + timedelta(days=random.randint(0, 20))
        if moment >= self.now:
            moment = self.now - timedelta(hours=random.randint(1, 72))

        try:
            redemption = ledger.redeem_reward(membership=membership, reward=reward, actor=cashier)
        except ledger.LedgerError:
            return 0

        self._backdate(redemption.ledger_entry, moment)

        # ‎١٨٪ من الأكواد لا تُصرَف. الصرف الكامل كان سيجعل «مكافآت
        # لم تُصرَف» صفرًا — وهي شريحة حقيقية يخطّط لها التاجر.
        if random.random() < 0.18:
            Redemption.objects.filter(pk=redemption.pk).update(
                status=Redemption.STATUS_EXPIRED, created_at=moment
            )
            return 1

        Redemption.objects.filter(pk=redemption.pk).update(
            status=Redemption.STATUS_USED,
            used_at=moment,
            used_by_staff=cashier,
            created_at=moment,
        )
        return 1

    def _balance_of(self, membership, reward) -> Decimal:
        from apps.loyalty.models import Balance

        row = Balance.objects.filter(membership=membership, program=reward.program).first()
        return row.amount if row else Decimal("0")

    # ═══════════════════════ الحملات ═══════════════════════

    def _seed_campaigns(self, brand: Brand) -> None:
        """
        حملات مُرسَلة بمهامّ رسائل حقيقية.

        معدّلات الوصول والتفاعل في شاشة الحملات تُحسب من
        `MessageJob` لا من عمود محفوظ. حملة بلا مهامّ تظهر «أُرسلت
        إلى ٠» — وهو ما يجعل الشاشة تبدو معطوبة.
        """
        members = list(
            Membership.objects.filter(brand=brand, customer__consent_at__isnull=False)
            .select_related("customer")
            .order_by("?")[:900]
        )
        if not members:
            return

        owner = StaffUser.objects.filter(branch__brand=brand, role=StaffUser.ROLE_OWNER).first()

        for index, (name, template, delivered_rate, read_rate) in enumerate(CAMPAIGN_SPECS):
            sent_at = self.now - timedelta(days=18 * (index + 1) + random.randint(0, 6))
            audience = members[: int(len(members) * random.uniform(0.28, 0.72))]

            campaign, created = Campaign.objects.get_or_create(
                brand=brand,
                name=name,
                defaults={
                    "created_by": owner,
                    "message_template": template,
                    "segment_query": {"active_within_days": 90},
                    "channel_priority": [Channel.PUSH, Channel.WHATSAPP, Channel.SMS],
                    "status": Campaign.STATUS_SENT,
                    "scheduled_at": sent_at,
                    "started_at": sent_at,
                    "finished_at": sent_at + timedelta(minutes=9),
                    "estimated_recipients": len(audience),
                },
            )
            if created:
                Campaign.objects.filter(pk=campaign.pk).update(created_at=sent_at)
            else:
                sent_at = campaign.started_at or campaign.created_at

            # الحملة قد تكون كُتبت في تشغيل سابق حين كانت القاعدة
            # أصغر، فتبقى «أُرسلت إلى ٢٠» فوق ألف عميل. تُستكمَل
            # لمن لا مهمّة له فيها بدل أن تُترك رقمًا لا يصدّقه أحد.
            already = set(
                MessageJob.objects.filter(campaign=campaign).values_list("customer_id", flat=True)
            )
            pending = [m for m in audience if m.customer_id not in already]
            if pending:
                self._message_jobs(campaign, pending, sent_at, delivered_rate, read_rate)

        # حملة واحدة مجدولة وأخرى مسوّدة: الشاشة فيها ثلاث حالات،
        # وقائمة كلها «أُرسلت» تترك مرشّحين فارغين بلا سبب ظاهر
        Campaign.objects.get_or_create(
            brand=brand,
            name="استرجاع الخاملين",
            defaults={
                "created_by": owner,
                "message_template": "{name}، رصيدك {balance} نقطة على وشك الانتهاء.",
                "segment_query": {"dormant_days": 90},
                "channel_priority": [Channel.PUSH, Channel.SMS],
                "status": Campaign.STATUS_SCHEDULED,
                "scheduled_at": self.now + timedelta(days=3),
                "estimated_recipients": len(members) // 3,
            },
        )
        Campaign.objects.get_or_create(
            brand=brand,
            name="عرض رمضان",
            defaults={
                "created_by": owner,
                "message_template": "رمضان كريم {name}! نقاط مضاعفة كل يوم بعد المغرب.",
                "segment_query": {},
                "channel_priority": [Channel.PUSH],
                "status": Campaign.STATUS_DRAFT,
            },
        )

    def _message_jobs(self, campaign, audience, sent_at, delivered_rate, read_rate) -> None:
        jobs = []
        for membership in audience:
            customer = membership.customer
            # القناة تتبع الموجّه الحقيقي: من ثبّت التطبيق يأخذ
            # إشعارًا مجانيًا، والباقي واتساب ثم رسالة نصية
            if customer.push_subscription:
                channel, cost = Channel.PUSH, Decimal("0")
            elif random.random() < 0.7:
                channel, cost = Channel.WHATSAPP, Decimal("0.1400")
            else:
                channel, cost = Channel.SMS, Decimal("0.3500")

            roll = random.random()
            if roll > delivered_rate:
                status, moment = MessageJob.STATUS_FAILED, None
            elif roll < read_rate:
                status, moment = MessageJob.STATUS_READ, sent_at
            else:
                status, moment = MessageJob.STATUS_DELIVERED, sent_at

            jobs.append(
                MessageJob(
                    campaign=campaign,
                    customer=customer,
                    channel=channel,
                    status=status,
                    cost=cost if status != MessageJob.STATUS_FAILED else Decimal("0"),
                    sent_at=moment,
                    created_at=sent_at,
                    error="" if status != MessageJob.STATUS_FAILED else "رقم غير قابل للوصول",
                )
            )

        MessageJob.objects.bulk_create(jobs, batch_size=500)

        # التكلفة والعدد يُعادان من **كل** مهامّ الحملة لا من الدفعة
        # الأخيرة: حملة استُكمِلت على مرحلتين كانت ستعلن تكلفة
        # المرحلة الثانية وحدها، فتبدو أرخص مما كلّفت فعلًا.
        totals = MessageJob.objects.filter(campaign=campaign).aggregate(
            spent=Sum("cost"), reached=Count("id")
        )
        spent = totals["spent"] or Decimal("0")
        Campaign.objects.filter(pk=campaign.pk).update(
            actual_cost=spent,
            estimated_cost=(spent * Decimal("1.1")).quantize(Decimal("0.0001")),
            estimated_recipients=totals["reached"] or 0,
        )

    # ═══════════════════════ مراجعة الإشارات ═══════════════════════

    def _review_signals(self, brand: Brand) -> int:
        """
        يُغلق جزءًا من إشارات الشذوذ القديمة.

        الإشارات كلها تأتي «مفتوحة» من `fraud.evaluate`. قائمة لم
        يُراجَع فيها شيء تجعل مؤشر «عمليات تحتاج مراجعة» يساوي عدد
        الإشارات الكلي أبدًا، فيبدو أن الشاشة لا تعمل.

        القديم وحده يُراجَع — الإشارات الحديثة تبقى مفتوحة لأنها
        بالضبط ما يُفترض أن يجده التاجر في انتظاره.
        """
        cutoff = self.now - timedelta(days=21)
        pending = list(
            FraudSignal.objects.filter(
                transaction__terminal__branch__brand=brand,
                status=FraudSignal.STATUS_OPEN,
                created_at__lt=cutoff,
            ).order_by("created_at")
        )

        reviewer = StaffUser.objects.filter(
            branch__brand=brand, role=StaffUser.ROLE_MANAGER
        ).first()

        closed = 0
        for signal in pending:
            if random.random() > 0.74:
                continue
            FraudSignal.objects.filter(pk=signal.pk).update(
                status=random.choice([FraudSignal.STATUS_ACCEPTED, FraudSignal.STATUS_REJECTED]),
                reviewed_by=reviewer,
                reviewed_at=signal.created_at + timedelta(hours=random.randint(2, 40)),
            )
            closed += 1
        return closed
