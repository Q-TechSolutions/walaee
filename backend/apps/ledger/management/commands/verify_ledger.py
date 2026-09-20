"""
تدقيق سلامة الأرصدة.

يقارن كل لقطة رصيد بمجموع قيودها. أي اختلاف يعني مسارًا يكتب في
الرصيد خارج `apply_entry` — وهو عطل يستوجب وقف النشر لا إصلاحًا
هادئًا، لأن رقمًا واحدًا خاطئًا يُسقط الثقة في كل الأرقام.

    python manage.py verify_ledger
    python manage.py verify_ledger --fix-snapshots   # بحذر شديد

يُستدعى تلقائيًا بعد كل استرجاع نسخة احتياطية، ويعمل ليليًا
كمهمة Celery — راجع apps/ledger/tasks.py
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum

from apps.ledger.models import LedgerEntry
from apps.loyalty.models import Balance


class Command(BaseCommand):
    help = "يقارن لقطات الأرصدة بمجموع القيود ويبلّغ عن أي انحراف"

    def add_arguments(self, parser):
        parser.add_argument(
            "--fix-snapshots",
            action="store_true",
            help=(
                "يصحّح اللقطة لتطابق مجموع القيود. القيود مصدر الحقيقة، "
                "لكن استخدمه بعد فهم سبب الانحراف لا قبله."
            ),
        )
        parser.add_argument("--quiet", action="store_true", help="لا يطبع شيئًا إن كان كل شيء سليمًا")

    def handle(self, *args, **options):
        drifted = []
        checked = 0

        balances = Balance.objects.select_related(
            "membership__customer", "membership__brand", "program"
        ).iterator(chunk_size=500)

        for balance in balances:
            checked += 1
            total = LedgerEntry.objects.filter(
                membership_id=balance.membership_id, program_id=balance.program_id
            ).aggregate(total=Sum("delta"))["total"] or Decimal("0")

            if total != balance.amount:
                drifted.append((balance, total))

        if not drifted:
            if not options["quiet"]:
                self.stdout.write(self.style.SUCCESS(f"✓ سليم — فُحصت {checked} محفظة"))
            return

        self.stdout.write(self.style.ERROR(f"✗ انحراف في {len(drifted)} من {checked} محفظة"))
        self.stdout.write("")

        for balance, total in drifted[:50]:
            self.stdout.write(
                f"  {balance.membership.brand.name} · "
                f"{balance.membership.customer.phone} · {balance.program.name}"
            )
            self.stdout.write(
                f"    اللقطة {balance.amount}  ·  مجموع القيود {total}  ·  "
                f"الفرق {balance.amount - total}"
            )

        if len(drifted) > 50:
            self.stdout.write(f"  … و {len(drifted) - 50} أخرى")

        if not options["fix_snapshots"]:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "لم يُصحَّح شيء. ابحث عن المسار الذي يكتب في الرصيد خارج\n"
                    "apply_entry أولًا — التصحيح بلا فهم السبب يخفي العطل\n"
                    "ويتركه يتكرر. ثم شغّل الأمر بـ--fix-snapshots."
                )
            )
            raise SystemExit(1)

        with transaction.atomic():
            for balance, total in drifted:
                Balance.objects.filter(pk=balance.pk).update(amount=total)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"✓ صُحّحت {len(drifted)} لقطة لتطابق قيودها"))
