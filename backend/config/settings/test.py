"""
إعدادات الاختبارات.

PostgreSQL إلزامي وليس SQLite: اختبارات التزامن تعتمد على
SELECT FOR UPDATE وسلوك القفل الحقيقي — docs/architecture/testing.md
"""

from .base import *  # noqa: F401,F403
from .base import DATABASES

DEBUG = False
SMS_PROVIDER = "console"

# تسريع الاختبارات — التجزئة القوية غير مطلوبة هنا
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

DATABASES["default"]["ATOMIC_REQUESTS"] = False
