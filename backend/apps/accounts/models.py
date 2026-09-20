"""
الحسابات والهويات.

قرار معماري: `User` و `Customer` كيانان منفصلان.
`User` لأصحاب المتاجر وفريق المنصة — يملك كلمة مرور ويدخل لوحات.
`Customer` للعميل النهائي — يدخل بالهاتف و OTP فقط ولا كلمة مرور له.
دمجهما كان سيفرض على كل عميل حسابًا كامل الصلاحيات بلا داعٍ، ويجعل
عزل بيانات العلامات أصعب.

المرجع: docs/architecture/data-model.md — القسم ١
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel, SoftDeleteModel, UUIDModel

from .validators import normalize_phone, phone_validator


class UserManager(BaseUserManager):
    """الهاتف هو المعرّف لا البريد."""

    use_in_migrations = True

    def _create(self, phone, password, **extra):
        if not phone:
            raise ValueError("رقم الهاتف مطلوب.")
        phone = normalize_phone(phone)
        user = self.model(phone=phone, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, phone, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create(phone, password, **extra)

    def create_superuser(self, phone, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_active", True)
        if extra.get("is_staff") is not True:
            raise ValueError("المستخدم الخارق يجب أن يكون is_staff=True")
        if extra.get("is_superuser") is not True:
            raise ValueError("المستخدم الخارق يجب أن يكون is_superuser=True")
        return self._create(phone, password, **extra)


class User(UUIDModel, AbstractBaseUser, PermissionsMixin):
    """حساب النظام — لأصحاب المتاجر وفريق المنصة."""

    phone = models.CharField("الهاتف", max_length=20, unique=True, validators=[phone_validator])
    email = models.EmailField("البريد", blank=True)
    full_name = models.CharField("الاسم الكامل", max_length=120, blank=True)
    is_active = models.BooleanField("نشط", default=True)
    is_staff = models.BooleanField("وصول لوحة الإدارة", default=False)
    is_platform_admin = models.BooleanField("مدير منصة", default=False)
    date_joined = models.DateTimeField(default=timezone.now, editable=False)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "مستخدم"
        verbose_name_plural = "المستخدمون"
        ordering = ("-date_joined",)

    def __str__(self) -> str:
        return self.full_name or self.phone

    def save(self, *args, **kwargs):
        self.phone = normalize_phone(self.phone)
        return super().save(*args, **kwargs)


class Customer(SoftDeleteModel):
    """
    العميل النهائي — هوية واحدة عبر المنصة كلها.

    `consent_at` و `consent_version` مطلوبان للامتثال: لا تُرسَل أي رسالة
    تسويقية لعميل بلا موافقة مسجّلة بتاريخها ونسخة النص الذي وافق عليه.
    """

    phone = models.CharField("الهاتف", max_length=20, unique=True, validators=[phone_validator])
    full_name = models.CharField("الاسم", max_length=120, blank=True)
    birth_date = models.DateField("تاريخ الميلاد", null=True, blank=True)

    # يسمحان لـ DRF بمعاملة العميل كهوية مصادَق عليها. العميل ليس
    # `User` ولا يملك أي صلاحية إدارية — التمييز عبر IsCustomer.
    is_authenticated = True
    is_anonymous = False

    consent_at = models.DateTimeField("تاريخ الموافقة", null=True, blank=True)
    consent_version = models.CharField("نسخة النص", max_length=20, blank=True)

    push_subscription = models.JSONField("اشتراك الإشعارات", null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "عميل"
        verbose_name_plural = "العملاء"
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["phone"], name="customer_phone_idx")]

    def __str__(self) -> str:
        return self.full_name or self.phone

    def save(self, *args, **kwargs):
        self.phone = normalize_phone(self.phone)
        return super().save(*args, **kwargs)

    @property
    def has_consent(self) -> bool:
        return self.consent_at is not None

    def anonymize(self) -> None:
        """
        إخفاء الهوية بدل الحذف.

        القيود تبقى بمعرّف مجهول فيظل رصيد التاجر متوازنًا، وتختفي
        بيانات العميل الشخصية — docs/architecture/security.md
        """
        self.full_name = ""
        self.birth_date = None
        self.push_subscription = None
        self.consent_at = None
        self.consent_version = ""
        self.phone = f"deleted-{self.pk.hex[:12]}"
        self.deleted_at = self.deleted_at or timezone.now()
        self.save(
            update_fields=[
                "full_name",
                "birth_date",
                "push_subscription",
                "consent_at",
                "consent_version",
                "phone",
                "deleted_at",
                "updated_at",
            ]
        )


class OtpCode(BaseModel):
    """
    كود تحقق لمرة واحدة.

    الكود يُخزَّن مُجزّأً لا نصًا صريحًا: من يقرأ الجدول لا يستطيع
    انتحال هوية عميل لم يستلم رسالته بعد.
    """

    PURPOSE_LOGIN = "login"
    PURPOSE_DELETE = "delete_account"
    PURPOSE_CHOICES = [
        (PURPOSE_LOGIN, "تسجيل الدخول"),
        (PURPOSE_DELETE, "حذف الحساب"),
    ]

    phone = models.CharField(max_length=20, db_index=True, validators=[phone_validator])
    code_hash = models.CharField(max_length=128)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, default=PURPOSE_LOGIN)
    expires_at = models.DateTimeField(db_index=True)
    consumed_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    request_ip = models.GenericIPAddressField(null=True, blank=True)

    MAX_ATTEMPTS = 5

    class Meta:
        verbose_name = "كود تحقق"
        verbose_name_plural = "أكواد التحقق"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["phone", "purpose", "-created_at"], name="otp_lookup_idx"),
        ]

    def __str__(self) -> str:
        return f"OTP {self.phone} ({self.purpose})"

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def is_usable(self) -> bool:
        return (
            self.consumed_at is None and not self.is_expired and self.attempts < self.MAX_ATTEMPTS
        )
