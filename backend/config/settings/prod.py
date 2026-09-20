"""بيئة الإنتاج."""

from .base import *  # noqa: F401,F403
from .base import env_bool, env_str

DEBUG = False

# ── رؤوس وضوابط الأمان ──────────────────────────────
# التحويل إلى https مُفعَّل افتراضيًا، وقابل للإطفاء صراحةً.
#
# السبب: خلف Traefik يصل الطلب ومعه X-Forwarded-Proto=https فلا
# تحويل. لكن نشرًا تجريبيًا على http مباشرة بلا شهادة يعني أن كل
# نداء API يُقابَل بـ301 إلى https لا يستمع إليه أحد — فيرى
# المستخدم «Failed to fetch» بلا أي أثر في السجل يشرح السبب.
#
# اضبطه 0 للنشر التجريبي وحده. في الإنتاج الحقيقي يبقى 1.
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ملفات تعريف آمنة فقط فوق https. إبقاؤها مفعّلة على نشر http
# يمنع الجلسة من الحفظ أصلًا، فيبدو الدخول ناجحًا ثم يُطرَد
# المستخدم فورًا.
_SECURE_COOKIES = SECURE_SSL_REDIRECT

# الفحص الصحي يأتي من داخل الحاوية على http بلا أي رأس وكيل.
# بدون هذا الاستثناء يردّ بـ301 فيبدو ناجحًا لـcurl وهو لم يلمس
# قاعدة البيانات أصلًا — فحص أخضر كاذب أسوأ من غياب الفحص.
SECURE_REDIRECT_EXEMPT = [r"^healthz$"]
# HSTS يجبر المتصفح على https لسنة — كارثة على نشر http
SECURE_HSTS_SECONDS = 31536000 if SECURE_SSL_REDIRECT else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SESSION_COOKIE_SECURE = _SECURE_COOKIES
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = _SECURE_COOKIES
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
