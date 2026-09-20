"""
الإعدادات المشتركة بين كل البيئات.

المرجع: docs/architecture/README.md و docs/architecture/security.md
لا تُوضع هنا أي قيمة سرية — كل الأسرار من متغيرات البيئة.
"""

from datetime import timedelta
from pathlib import Path

from .env import env_bool, env_int, env_list, env_str

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ═══════════════════════ أساسي ═══════════════════════

SECRET_KEY = env_str("SECRET_KEY", "insecure-development-key-change-me")
DEBUG = env_bool("DEBUG", False)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", ["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", [])

# ═══════════════════════ التطبيقات ═══════════════════════

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "django_celery_beat",
]

# ترتيب مقصود: common أولًا لأن البقية ترث منه،
# ثم tenancy قبل loyalty قبل ledger — اتجاه الاعتماد نفسه.
LOCAL_APPS = [
    "apps.common",
    "apps.accounts",
    "apps.tenancy",
    "apps.loyalty",
    "apps.ledger",
    "apps.audit",
    "apps.fraud",
    "apps.pos",
    # المرحلة الثانية — مسجّلة بلا نماذج بعد
    "apps.campaigns",
    "apps.billing",
    # مؤجّلة بمفاتيح ميزات — تُسجَّل شرطيًا أسفل الملف
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ═══════════════════════ مفاتيح الميزات ═══════════════════════
# الباقات الثلاث من قاعدة كود واحدة. الترقية = متغيّر بيئة ونشر.

FEATURE_PUBLIC_API = env_bool("FEATURE_PUBLIC_API", False)
FEATURE_AI_INSIGHTS = env_bool("FEATURE_AI_INSIGHTS", False)

if FEATURE_PUBLIC_API:
    INSTALLED_APPS.append("apps.publicapi")
if FEATURE_AI_INSIGHTS:
    INSTALLED_APPS.append("apps.insights")

# ═══════════════════════ الوسائط ═══════════════════════

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # يلتقط الفاعل و IP لكل طلب ليستخدمهما سجل التدقيق
    "apps.audit.middleware.AuditContextMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ═══════════════════════ قاعدة البيانات ═══════════════════════

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env_str("POSTGRES_DB", "walaee"),
        "USER": env_str("POSTGRES_USER", "walaee"),
        "PASSWORD": env_str("POSTGRES_PASSWORD", "walaee"),
        "HOST": env_str("POSTGRES_HOST", "127.0.0.1"),
        "PORT": env_str("POSTGRES_PORT", "5433"),
        "CONN_MAX_AGE": env_int("CONN_MAX_AGE", 60),
        "ATOMIC_REQUESTS": False,
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ═══════════════════════ المصادقة ═══════════════════════

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

# عمر التوكن — docs/architecture/security.md
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ═══════════════════════ DRF ═══════════════════════

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("apps.accounts.authentication.WalaeeJWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.DefaultPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.common.exceptions.walaee_exception_handler",
    # حدود OTP معرّفة في apps/accounts/throttles.py بنوافذ صريحة:
    # صيغة DEFAULT_THROTTLE_RATES لا تستطيع تمثيل «٣ لكل ١٥ دقيقة».
}

SPECTACULAR_SETTINGS = {
    "TITLE": "ولائي — Walaee API",
    "DESCRIPTION": "منصة إدارة برامج الولاء متعددة المتاجر",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/v1",
    # عدة نماذج تسمّي حقلها `status`، والتسمية التلقائية تولّد
    # أسماء مثل Status6e4Enum في العميل المولَّد — لا تُقرأ ولا تُصان.
    "ENUM_NAME_OVERRIDES": {
        "TransactionStatusEnum": "apps.ledger.models.Transaction.STATUS_CHOICES",
        "RedemptionStatusEnum": "apps.ledger.models.Redemption.STATUS_CHOICES",
        "CampaignStatusEnum": "apps.campaigns.models.Campaign.STATUS_CHOICES",
        "MessageJobStatusEnum": "apps.campaigns.models.MessageJob.STATUS_CHOICES",
        "SubscriptionStatusEnum": "apps.billing.models.Subscription.STATUS_CHOICES",
        "InvoiceStatusEnum": "apps.billing.models.Invoice.STATUS_CHOICES",
        "FraudSignalStatusEnum": "apps.fraud.models.FraudSignal.STATUS_CHOICES",
        "MembershipStatusEnum": "apps.loyalty.models.Membership.STATUS_CHOICES",
        "OrganizationStatusEnum": "apps.tenancy.models.Organization.STATUS_CHOICES",
    },
}

# ═══════════════════════ Redis و Celery ═══════════════════════

REDIS_URL = env_str("REDIS_URL", "redis://127.0.0.1:6380/0")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

CELERY_BROKER_URL = env_str("CELERY_BROKER_URL", "redis://127.0.0.1:6380/1")
CELERY_RESULT_BACKEND = env_str("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6380/2")
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TIMEZONE = "Africa/Cairo"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# عزل الطوابير غير قابل للتفاوض — docs/architecture/async-tasks.md
CELERY_TASK_ROUTES = {
    "apps.pos.tasks.rotate_codes": {"queue": "realtime"},
    "apps.pos.tasks.notify_customer": {"queue": "realtime"},
    "apps.ledger.tasks.*": {"queue": "maintenance"},
    "apps.campaigns.tasks.*": {"queue": "messaging"},
    "apps.fraud.tasks.*": {"queue": "analytics"},
}

# ═══════════════════════ الولاء ونقطة البيع ═══════════════════════

POS_CODE_TTL_SECONDS = env_int("POS_CODE_TTL_SECONDS", 35)
POS_CODE_ROTATE_SECONDS = env_int("POS_CODE_ROTATE_SECONDS", 30)
REDEMPTION_CODE_TTL_MINUTES = env_int("REDEMPTION_CODE_TTL_MINUTES", 15)
DEFAULT_EXPIRY_MONTHS = env_int("DEFAULT_EXPIRY_MONTHS", 12)
OTP_TTL_SECONDS = env_int("OTP_TTL_SECONDS", 300)
OTP_LENGTH = env_int("OTP_LENGTH", 6)

# ═══════════════════════ القنوات ═══════════════════════
# لا يُستورَد أي SDK لمزوّد هنا. القرارات ٧ و ٨ في
# docs/planning/decisions.md لم تُحسم بعد، فالتكامل خلف واجهة مجرّدة.

SMS_PROVIDER = env_str("SMS_PROVIDER", "console")
SMS_API_KEY = env_str("SMS_API_KEY", "")
SMS_SENDER_ID = env_str("SMS_SENDER_ID", "WALAEE")
PAYMENT_GATEWAY = env_str("PAYMENT_GATEWAY", "none")
PAYMENT_API_KEY = env_str("PAYMENT_API_KEY", "")
VAPID_PUBLIC_KEY = env_str("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = env_str("VAPID_PRIVATE_KEY", "")

# ═══════════════════════ التدويل ═══════════════════════

LANGUAGE_CODE = "ar"
TIME_ZONE = "Africa/Cairo"
USE_I18N = True
USE_TZ = True
LOCALE_PATHS = [BASE_DIR / "locale"]

# ═══════════════════════ الملفات الثابتة ═══════════════════════

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# ═══════════════════════ السجلّات ═══════════════════════

LOG_LEVEL = env_str("LOG_LEVEL", "INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s %(levelname)-8s %(name)s | %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        # محرك القيود يُسجَّل دائمًا بالتفصيل — أي خلل فيه يجب أن يكون مرئيًا
        "apps.ledger": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "django.db.backends": {"level": "WARNING"},
    },
}
