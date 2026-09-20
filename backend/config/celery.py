"""
تطبيق Celery.

عزل الطوابير مُعرَّف في CELERY_TASK_ROUTES داخل الإعدادات.
المرجع: docs/architecture/async-tasks.md
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("walaee")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
