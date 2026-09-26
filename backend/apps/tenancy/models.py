"""
التسلسل التنظيمي: مؤسسة ← علامة ← فرع ← نقطة بيع ← كاشير.

يُبنى كاملًا من اليوم صفر حتى لو كان أول عميل متجرًا واحدًا بفرع واحد.
إضافة مستوى لاحقًا تعني هجرة تمسّ كل جدول يحمل مرجعًا للعلامة، وهي
أغلى بمراتب من إنشاء الجداول فارغة الآن.

المرجع: docs/architecture/data-model.md — القسم ١
"""

from django.db import models

from apps.common.models import BaseModel

from .geo import GOVERNORATE_CHOICES
from .managers import BrandScopedQuerySet


class Organization(BaseModel):
    """كيان التعاقد والفوترة — أعلى مستوى في الشجرة."""

    STATUS_ACTIVE = "active"
    STATUS_SUSPENDED = "suspended"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "نشطة"),
        (STATUS_SUSPENDED, "موقوفة"),
    ]

    name = models.CharField("الاسم", max_length=160)
    legal_name = models.CharField("الاسم القانوني", max_length=200, blank=True)
    tax_id = models.CharField("الرقم الضريبي", max_length=40, blank=True)
    billing_email = models.EmailField("بريد الفوترة", blank=True)
    status = models.CharField(
        "الحالة", max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE
    )

    class Meta:
        verbose_name = "مؤسسة"
        verbose_name_plural = "المؤسسات"
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Brand(BaseModel):
    """
    العلامة التجارية — وحدة عزل البيانات.

    عميل العلامة «أ» لا يظهر للعلامة «ب» إطلاقًا. كل استعلام يمسّ بيانات
    عملاء يمر عبر BrandScopedQuerySet.
    """

    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="brands", verbose_name="المؤسسة"
    )
    slug = models.SlugField("المعرّف", max_length=60, unique=True)
    name = models.CharField("الاسم", max_length=120)
    category = models.CharField("الفئة", max_length=60, blank=True)
    tagline = models.CharField(
        "الوصف المختصر",
        max_length=120,
        blank=True,
        help_text="سطر واحد يظهر في الدليل العام وبطاقة العميل.",
    )
    logo = models.ImageField("الشعار", upload_to="brands/", blank=True, null=True)
    primary_color = models.CharField("اللون الأساسي", max_length=7, default="#1F6F5C")
    is_active = models.BooleanField("نشطة", default=True)
    # الظهور في الدليل قرار تجاري منفصل عن التشغيل: علامة قد تعمل
    # على المنصة وهي لا تريد أن تُعلَن قبل افتتاحها، وتعطيلها
    # لتحقيق ذلك يقطع برنامج ولائها عن عملائه.
    is_listed = models.BooleanField(
        "تظهر في الدليل العام",
        default=True,
        help_text="إخفاؤها لا يوقف برنامجها — يمنع ظهورها في الخريطة والصفحة العامة فقط.",
    )
    joined_on = models.DateField("تاريخ التعاقد", null=True, blank=True)

    class Meta:
        verbose_name = "علامة تجارية"
        verbose_name_plural = "العلامات التجارية"
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class Branch(BaseModel):
    """الفرع — `lat`/`lng` مفهرسان لخاصية «متاجر قريبة منك»."""

    brand = models.ForeignKey(
        Brand, on_delete=models.CASCADE, related_name="branches", verbose_name="العلامة"
    )
    name = models.CharField("الاسم", max_length=120)
    address = models.CharField("العنوان", max_length=255, blank=True)
    city = models.CharField("المدينة", max_length=80, blank=True)
    # الرمز لا الاسم: اسم المحافظة يُكتب بأربع صيغ مختلفة («القاهره»،
    # «القاهرة»، «Cairo»…) فيتفتّت التجميع في الخريطة إلى صفوف مكرّرة
    # لا يجمعها شيء. الرمز يأتي من apps.tenancy.geo وحده.
    governorate = models.CharField(
        "المحافظة", max_length=3, choices=GOVERNORATE_CHOICES, blank=True, db_index=True
    )
    lat = models.DecimalField("خط العرض", max_digits=9, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField("خط الطول", max_digits=9, decimal_places=6, null=True, blank=True)
    opening_hours = models.JSONField("مواعيد العمل", null=True, blank=True)
    is_active = models.BooleanField("نشط", default=True)

    objects = BrandScopedQuerySet.as_manager()

    class Meta:
        verbose_name = "فرع"
        verbose_name_plural = "الفروع"
        ordering = ("brand__name", "name")
        indexes = [models.Index(fields=["lat", "lng"], name="branch_geo_idx")]

    def __str__(self) -> str:
        return f"{self.brand.name} — {self.name}"


class Terminal(BaseModel):
    """
    نقطة البيع.

    `current_code` نسخة للتدقيق فقط. الرمز الفعّال يعيش في Redis بـ TTL
    لأن القراءة عند كل مسح يجب أن تكون بلا لمس قاعدة البيانات.
    """

    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, related_name="terminals", verbose_name="الفرع"
    )
    label = models.CharField("التسمية", max_length=60)
    current_code = models.CharField("الرمز الحالي", max_length=12, blank=True)
    code_expires_at = models.DateTimeField("انتهاء الرمز", null=True, blank=True)
    is_active = models.BooleanField("نشطة", default=True)

    class Meta:
        verbose_name = "نقطة بيع"
        verbose_name_plural = "نقاط البيع"
        ordering = ("branch__name", "label")

    def __str__(self) -> str:
        return f"{self.branch.name} / {self.label}"

    @property
    def brand_id(self):
        return self.branch.brand_id


class StaffUser(BaseModel):
    """
    الكاشير والموظف — حساب مستقل لكل شخص.

    الحساب المشترك بين كاشيرين يجعل كشف الاحتيال مستحيلًا: لا يمكن
    نسبة نمط مشبوه إلى شخص بعينه.
    """

    ROLE_OWNER = "owner"
    ROLE_MANAGER = "manager"
    ROLE_CASHIER = "cashier"
    ROLE_CHOICES = [
        (ROLE_OWNER, "مالك"),
        (ROLE_MANAGER, "مدير"),
        (ROLE_CASHIER, "كاشير"),
    ]

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="staff_roles",
        verbose_name="المستخدم",
    )
    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, related_name="staff", verbose_name="الفرع"
    )
    role = models.CharField("الدور", max_length=20, choices=ROLE_CHOICES, default=ROLE_CASHIER)
    pin_hash = models.CharField("تجزئة الرمز السري", max_length=128, blank=True)
    is_active = models.BooleanField("نشط", default=True)

    class Meta:
        verbose_name = "موظف"
        verbose_name_plural = "الموظفون"
        ordering = ("branch__name", "role")
        constraints = [
            models.UniqueConstraint(fields=["user", "branch"], name="unique_staff_per_branch")
        ]

    def __str__(self) -> str:
        return f"{self.user} — {self.get_role_display()} @ {self.branch.name}"

    @property
    def brand_id(self):
        return self.branch.brand_id

    @property
    def can_view_reports(self) -> bool:
        """الكاشير يؤكّد العمليات ولا يرى التقارير — security.md"""
        return self.role in (self.ROLE_OWNER, self.ROLE_MANAGER)

    @property
    def can_manage_brand(self) -> bool:
        return self.role == self.ROLE_OWNER
