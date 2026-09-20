"""بيئة الإنتاج."""

from .base import *  # noqa: F401,F403
from .base import env_str

DEBUG = False

# ── رؤوس وضوابط الأمان ──────────────────────────────
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [o for o in env_str("CORS_ALLOWED_ORIGINS", "").split(",") if o]

_sentry_dsn = env_str("SENTRY_DSN", "")
if _sentry_dsn:  # pragma: no cover - لا يُفعَّل في الاختبارات
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=_sentry_dsn,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,  # أرقام الهواتف لا تُرسَل
    )
