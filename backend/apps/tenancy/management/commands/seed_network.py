"""
ينشئ شبكة التجّار المتعاقدين من كتالوج `apps.tenancy.network`.

يُشغَّل في الإنتاج. لا ينشئ حسابًا واحدًا ولا عميلًا ولا عملية —
لا شيء هنا «تجريبي»: مؤسسات وعلامات وفروع وبرامج ومكافآت، وهي
بالضبط ما تعرضه الخريطة والصفحة العامة.

    python manage.py seed_network
    python manage.py seed_network --dry-run
    python manage.py seed_network --prune-branches

إعادة التشغيل آمنة: كل صف يُطابَق بمفتاح ثابت (سلاگ العلامة، اسم
الفرع داخلها) ويُحدَّث لا يُكرَّر. ما يعدّله التاجر بنفسه لاحقًا —
اسم الفرع أو لونه — لا يُداس إلا بـ`--force`، وإلا صار كل نشر
يمسح عمل التجّار ويعيدهم إلى نص الكتالوج.

الحذف ليس افتراضيًا: فرع أُزيل من الكتالوج قد يكون فرعًا حقيقيًا
عليه أرصدة عملاء. `--prune-branches` يُبطّله (`is_active=False`)
ولا يحذفه، فيختفي من الخريطة ويبقى تاريخه سليمًا في دفتر القيود.
"""

from __future__ import annotations

from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.billing.models import PLAN_LIMITS, Plan, Subscription
from apps.billing.services import get_subscription
from apps.loyalty.models import LoyaltyProgram, ProgramRule, Reward
from apps.tenancy.models import Branch, Brand, Organization, Terminal
from apps.tenancy.network import NETWORK, BrandSpec


def plan_for(branch_count: int) -> str:
    """الباقة التي تتسع فعلًا لعدد فروع العلامة.

    اشتقاقها من العدد لا كتابتها في الكتالوج: كتابتها يدويًا تعني
    علامة بسبعة فروع على باقة حدّها خمسة، فيفشل أول إنشاء فرع من
    لوحة التاجر برسالة «بلغت حد الباقة» بلا أن يفهم أحد لماذا.
    """
    for plan in (Plan.STARTER, Plan.GROWTH):
        limit = PLAN_LIMITS[plan]["max_branches"]
        if limit is not None and branch_count <= limit:
            return plan
    return Plan.CHAIN


class Command(BaseCommand):
    help = "ينشئ أو يحدّث شبكة التجّار المتعاقدين"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="يعرض ما سيتغيّر بلا كتابة شيء",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="يعيد كل صف إلى نص الكتالوج ولو عدّله التاجر",
        )
        parser.add_argument(
            "--prune-branches",
            action="store_true",
            help="يُبطّل الفروع التي لم تعد في الكتالوج (لا يحذفها)",
        )
        parser.add_argument("--only", help="سلاگ علامة واحدة بدل الشبكة كلها")

    def handle(self, *args, **options):
        self.dry = options["dry_run"]
        self.force = options["force"]
        self.created = {"org": 0, "brand": 0, "branch": 0, "terminal": 0, "program": 0, "reward": 0}
        self.updated = {"brand": 0, "branch": 0}
        self.disabled = 0

        specs = NETWORK
        if options["only"]:
            specs = tuple(s for s in NETWORK if s.slug == options["only"])
            if not specs:
                self.stderr.write(self.style.ERROR(f"لا توجد علامة بالسلاگ {options['only']}"))
                return

        # معاملة واحدة للشبكة كلها: شبكة نصفها منشأ ونصفها لا تعني
        # خريطة تعرض تغطية كاذبة إلى أن ينجح تشغيل تالٍ.
        with transaction.atomic():
            for spec in specs:
                self._brand(spec, prune=options["prune_branches"])

            if self.dry:
                transaction.set_rollback(True)

        self._report()

    # ── العلامة ومؤسستها ───────────────────────────────────

    def _brand(self, spec: BrandSpec, *, prune: bool) -> None:
        organization = self._organization(spec.organization)
        brand = Brand.objects.filter(slug=spec.slug).first()

        values = {
            "organization": organization,
            "name": spec.name,
            "category": spec.category,
            "tagline": spec.tagline,
            "primary_color": spec.color,
            "is_active": True,
            "is_listed": True,
            "joined_on": date.fromisoformat(spec.joined_on),
        }

        if brand is None:
            brand = Brand(slug=spec.slug, **values)
            if not self.dry:
                brand.save()
            self.created["brand"] += 1
            self.stdout.write(f"  + علامة {spec.name}")
        else:
            changed = self._apply(
                brand,
                values,
                # ما يملكه التاجر: الاسم واللون والوصف. الكتالوج يضعها
                # مرة عند التعاقد ثم يتركها له.
                owned={"name", "primary_color", "tagline"},
            )
            if changed:
                self.updated["brand"] += 1
                self.stdout.write(f"  ~ علامة {spec.name}: {', '.join(changed)}")

        self._subscription(organization, len(spec.branches))
        self._branches(brand, spec, prune=prune)
        self._program(brand, spec)

    def _organization(self, name: str) -> Organization:
        organization = Organization.objects.filter(name=name).first()
        if organization is not None:
            return organization

        organization = Organization(name=name, status=Organization.STATUS_ACTIVE)
        if not self.dry:
            organization.save()
        self.created["org"] += 1
        self.stdout.write(f"+ مؤسسة {name}")
        return organization

    def _subscription(self, organization: Organization, branch_count: int) -> None:
        if self.dry and organization.pk is None:
            return

        subscription = get_subscription(organization)
        plan = plan_for(branch_count)

        # لا يُخفَّض اشتراك قائم: مؤسسة رُقّيت يدويًا إلى «سلاسل»
        # لأنها افتتحت فروعًا خارج الكتالوج ستُنزَّل عند كل نشر.
        order = [Plan.FREE, Plan.STARTER, Plan.GROWTH, Plan.CHAIN]
        if order.index(plan) <= order.index(subscription.plan) and not self.force:
            return

        subscription.plan = plan
        subscription.status = Subscription.STATUS_ACTIVE
        subscription.mrr = PLAN_LIMITS[plan]["monthly_price"]
        if not self.dry:
            subscription.save(update_fields=["plan", "status", "mrr", "updated_at"])

    # ── الفروع ونقاط البيع ─────────────────────────────────

    def _branches(self, brand: Brand, spec: BrandSpec, *, prune: bool) -> None:
        seen: set[str] = set()

        for item in spec.branches:
            seen.add(item.name)
            values = {
                "address": item.address,
                "city": item.city,
                "governorate": item.governorate,
                "lat": item.lat,
                "lng": item.lng,
                "is_active": True,
            }

            branch = (
                Branch.objects.filter(brand=brand, name=item.name).first() if brand.pk else None
            )

            if branch is None:
                branch = Branch(brand=brand, name=item.name, **values)
                if not self.dry:
                    branch.save()
                self.created["branch"] += 1
            else:
                changed = self._apply(branch, values, owned={"address"})
                if changed:
                    self.updated["branch"] += 1

            self._terminals(branch, item.terminals)

        if prune and brand.pk:
            stale = Branch.objects.filter(brand=brand, is_active=True).exclude(name__in=seen)
            for branch in stale:
                self.stdout.write(self.style.WARNING(f"  ! تعطيل فرع {branch.name}"))
                if not self.dry:
                    branch.is_active = False
                    branch.save(update_fields=["is_active", "updated_at"])
                self.disabled += 1

    def _terminals(self, branch: Branch, count: int) -> None:
        if not branch.pk:
            # جفاف: الفرع لم يُكتب، فلا نقاط بيع تُحسب عليه
            self.created["terminal"] += count
            return

        existing = Terminal.objects.filter(branch=branch).count()
        for index in range(existing, count):
            if not self.dry:
                Terminal.objects.create(branch=branch, label=f"كاشير {index + 1}")
            self.created["terminal"] += 1

    # ── البرنامج وقواعده ومكافآته ──────────────────────────

    def _program(self, brand: Brand, spec: BrandSpec) -> None:
        if not brand.pk:
            self.created["program"] += 1
            self.created["reward"] += len(spec.program.rewards)
            return

        plan = spec.program
        program = LoyaltyProgram.objects.filter(brand=brand, name=plan.name).first()

        if program is None:
            program = LoyaltyProgram(brand=brand, type=plan.type, name=plan.name, is_active=True)
            if not self.dry:
                program.save()
            self.created["program"] += 1

        # القواعد تُكتب مرة عند الإنشاء ولا تُلمس بعدها: تعديل
        # `earn_rate` لبرنامج جارٍ يغيّر قيمة رصيد كسبه العملاء
        # بالفعل — قرار تجاري لا يُتخذ من أمر نشر.
        if program.pk and not ProgramRule.objects.filter(program=program).exists():
            if not self.dry:
                ProgramRule.objects.create(
                    program=program,
                    earn_rate=plan.earn_rate,
                    min_invoice=plan.min_invoice,
                    max_per_day=plan.max_per_day,
                    expiry_months=plan.expiry_months,
                    welcome_bonus=plan.welcome_bonus,
                    reversal_policy=ProgramRule.REVERSAL_MANAGER,
                )

        unit = Reward.UNIT_STAMPS if plan.type == LoyaltyProgram.TYPE_STAMPS else Reward.UNIT_POINTS
        for reward in plan.rewards:
            if not program.pk:
                self.created["reward"] += 1
                continue
            exists = Reward.objects.filter(program=program, title=reward.title).exists()
            if exists:
                continue
            if not self.dry:
                Reward.objects.create(
                    program=program,
                    title=reward.title,
                    description=reward.description,
                    cost_amount=reward.cost,
                    cost_unit=unit,
                    merchant_cost=reward.merchant_cost,
                    is_active=True,
                )
            self.created["reward"] += 1

    # ── أدوات ──────────────────────────────────────────────

    def _apply(self, instance, values: dict, *, owned: set[str]) -> list[str]:
        """يكتب الحقول المتغيّرة ويُرجع أسماءها.

        `owned` حقول يملكها التاجر: تُكتب عند الإنشاء فقط، ولا
        يعيدها إلى الكتالوج إلا `--force`.
        """
        changed: list[str] = []
        for field, value in values.items():
            if field in owned and not self.force:
                continue
            current = getattr(instance, field)
            # المقارنة نصًّا: الإحداثيات تعود من القاعدة Decimal
            # وتأتي من الكتالوج float، فالمقارنة المباشرة تقول
            # «تغيّر» في كل تشغيل ويمتلئ السجل بضجيج لا معنى له.
            if str(current) != str(value):
                setattr(instance, field, value)
                changed.append(field)

        if changed and not self.dry:
            instance.save(update_fields=[*changed, "updated_at"])
        return changed

    def _report(self) -> None:
        head = "معاينة — لم يُكتب شيء" if self.dry else "اكتملت"
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"شبكة التجّار: {head}"))
        self.stdout.write(
            "  جديد: "
            f"{self.created['org']} مؤسسة · "
            f"{self.created['brand']} علامة · "
            f"{self.created['branch']} فرع · "
            f"{self.created['terminal']} نقطة بيع · "
            f"{self.created['program']} برنامج · "
            f"{self.created['reward']} مكافأة"
        )
        self.stdout.write(f"  محدَّث: {self.updated['brand']} علامة · {self.updated['branch']} فرع")
        if self.disabled:
            self.stdout.write(f"  معطَّل: {self.disabled} فرع")
