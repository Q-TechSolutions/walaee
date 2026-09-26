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

# ══════════════════════════════════════════════════════════
#  حسابات التجربة مُطفأة في الاختبارات دائمًا.
#
#  `base` يقرؤها من البيئة، و.env الخاص بالمطوّر قد يشغّلها
#  لتجربة محلية. النتيجة أن اختبارًا يتحقّق من أن «الافتراضي
#  مُطفأ» ينجح على جهاز ويفشل على آخر بلا أن يتغيّر سطر كود —
#  وهو أسوأ نوع فشل لأنه يُفسَّر كخطأ عابر فيُعاد تشغيله لا أكثر.
#
#  ما يحتاج الميزة مُشغَّلة يطلبها صراحةً بـ`override_settings`،
#  فيقرأ كل اختبار شرطه من نفسه.
# ══════════════════════════════════════════════════════════
DEMO_LOGIN_PHONES: list[str] = []
DEMO_LOGIN_CODE = ""
DEMO_STAFF_PASSWORD = ""
DEMO_APP_URLS: list[str] = []
