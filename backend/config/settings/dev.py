"""بيئة التطوير المحلية."""

from .base import *  # noqa: F401,F403
from .base import REST_FRAMEWORK

DEBUG = True
ALLOWED_HOSTS = ["*"]

# واجهة OpenAPI مفتوحة محليًا للتصفّح
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
}

CORS_ALLOW_ALL_ORIGINS = True

# الرسائل تُطبع في الطرفية بدل إرسالها — لا مزوّد متعاقَد عليه بعد
SMS_PROVIDER = "console"

# تنفيذ مهام Celery فورًا داخل نفس العملية ما لم يُشغَّل عامل فعلي
CELERY_TASK_ALWAYS_EAGER = False
