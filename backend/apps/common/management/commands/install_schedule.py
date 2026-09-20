"""
تثبيت جدول المهام الدورية.

`django-celery-beat` يقرأ جدوله من قاعدة البيانات، وقاعدة إنتاج
جديدة تبدأ فارغة — فيعمل المجدول بلا أن ينفّذ شيئًا، ولا يظهر ذلك
في أي سجل. أول ما يُكتشف هو رصيد لم ينتهِ بعد سنة من موعده.

    python manage.py install_schedule

آمن لإعادة التشغيل: يُحدّث الموجود ولا يكرّره.
المرجع: docs/architecture/async-tasks.md
"""

import json

from django.core.management.base import BaseCommand
from django.db import transaction
from django_celery_beat.models import CrontabSchedule, IntervalSchedule, PeriodicTask

# (الاسم، المهمة، الجدولة، الطابور)
# الجدولة إما ("interval", كل كم ثانية) أو ("crontab", دقيقة، ساعة)
SCHEDULE = [
    (
        "تدوير رموز نقاط البيع",
        "apps.pos.tasks.rotate_codes",
        ("interval", 30),
        "realtime",
    ),
    (
        "إطلاق الحملات المجدولة",
        "apps.campaigns.tasks.dispatch_scheduled",
        ("interval", 300),
        "messaging",
    ),
    (
        "انتهاء صلاحية الأرصدة",
        "apps.ledger.tasks.expire_balances",
        ("crontab", 0, 3),
        "maintenance",
    ),
    (
        "تنبيه الأرصدة المقاربة للانتهاء",
        "apps.ledger.tasks.notify_expiring",
        ("crontab", 0, 10),
        "messaging",
    ),
    (
        "تدقيق سلامة الأرصدة",
        "apps.ledger.tasks.verify_integrity",
        ("crontab", 30, 2),
        "analytics",
    ),
    (
        "إصدار فواتير الاشتراكات",
        "apps.billing.tasks.charge_due_subscriptions",
        ("crontab", 0, 6),
        "billing",
    ),
    (
        "تعليم المتأخرين سدادًا",
        "apps.billing.tasks.flag_past_due",
        ("crontab", 30, 6),
        "billing",
    ),
]


class Command(BaseCommand):
    help = "يثبّت جدول المهام الدورية في قاعدة البيانات"

    def add_arguments(self, parser):
        parser.add_argument(
            "--prune",
            action="store_true",
            help="يحذف المهام الدورية التي لا يعرفها هذا الملف",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        installed = []

        for name, task, schedule, queue in SCHEDULE:
            kwargs = {
                "task": task,
                "queue": queue,
                "kwargs": json.dumps({}),
                "enabled": True,
            }

            if schedule[0] == "interval":
                interval, _ = IntervalSchedule.objects.get_or_create(
                    every=schedule[1], period=IntervalSchedule.SECONDS
                )
                kwargs["interval"] = interval
                kwargs["crontab"] = None
            else:
                _, minute, hour = schedule
                crontab, _ = CrontabSchedule.objects.get_or_create(
                    minute=str(minute),
                    hour=str(hour),
                    day_of_week="*",
                    day_of_month="*",
                    month_of_year="*",
                    timezone="Africa/Cairo",
                )
                kwargs["crontab"] = crontab
                kwargs["interval"] = None

            PeriodicTask.objects.update_or_create(name=name, defaults=kwargs)
            installed.append((name, task, queue))

        if options["prune"]:
            known = {name for name, _, _, _ in SCHEDULE}
            removed = PeriodicTask.objects.exclude(name__in=known).exclude(
                # المهمة المدمجة في الحزمة لا تُحذف
                name="celery.backend_cleanup"
            )
            count = removed.count()
            removed.delete()
            if count:
                self.stdout.write(self.style.WARNING(f"✗ حُذفت {count} مهمة غير معروفة"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"✓ ثُبّتت {len(installed)} مهمة دورية"))
        self.stdout.write("")
        for name, task, queue in installed:
            self.stdout.write(f"  {name:<32} [{queue:<12}] {task}")
        self.stdout.write("")
        self.stdout.write("  يمكن تعديل المواعيد من /django-admin/ دون نشر جديد.")
        self.stdout.write("")
