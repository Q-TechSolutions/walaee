"""
الاشتراكات والفوترة ورصيد الرسائل.

الجدار المجاني ليس تسويقًا: الرسائل تكلّف مالًا حقيقيًا لكل رسالة،
وبلا حد صارم يستطيع متجر واحد على الباقة المجانية أن يستهلك ميزانية
الرسائل الشهرية للمنصة كلها في يوم.

المرجع: docs/architecture/data-model.md — القسم ٤
"""

from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.common.models import AppendOnlyModel, BaseModel


class Plan(models.TextChoices):
    """
    الباقات وحدودها.

    الحدود هنا لا في قاعدة البيانات: تغيير حدّ لباقة يجب أن يمر
    بمراجعة كود ونشر، لا بتعديل صف يستطيع أي مدير عمله بالخطأ.
    """

    FREE = "free", "مجانية"
    STARTER = "starter", "أساسية"
    GROWTH = "growth", "نمو"
    CHAIN = "chain", "سلاسل"


# الحدود لكل باقة. None تعني بلا حد.
PLAN_LIMITS: dict[str, dict] = {
    Plan.FREE: {
        "max_branches": 1,
        "max_terminals": 1,
        "max_staff": 2,
        "max_programs": 1,
        "max_customers": 200,
        "monthly_free_messages": 0,
        "campaigns_enabled": False,
        "reports_export": False,
        "monthly_price": Decimal("0"),
    },
    Plan.STARTER: {
        "max_branches": 1,
        "max_terminals": 3,
        "max_staff": 5,
        "max_programs": 2,
        "max_customers": 2_000,
        "monthly_free_messages": 500,
        "campaigns_enabled": True,
        "reports_export": True,
        "monthly_price": Decimal("450"),
    },
    Plan.GROWTH: {
        "max_branches": 5,
        "max_terminals": 15,
        "max_staff": 25,
        "max_programs": 4,
        "max_customers": 20_000,
        "monthly_free_messages": 3_000,
        "campaigns_enabled": True,
        "reports_export": True,
        "monthly_price": Decimal("1200"),
    },
    Plan.CHAIN: {
        "max_branches": None,
        "max_terminals": None,
        "max_staff": None,
        "max_programs": None,
        "max_customers": None,
        "monthly_free_messages": 10_000,
        "campaigns_enabled": True,
        "reports_export": True,
        "monthly_price": Decimal("3000"),
    },
}


class Subscription(BaseModel):
    """اشتراك واحد لكل مؤسسة."""

    STATUS_TRIAL = "trial"
    STATUS_ACTIVE = "active"
    STATUS_PAST_DUE = "past_due"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_TRIAL, "تجريبي"),
        (STATUS_ACTIVE, "نشط"),
        (STATUS_PAST_DUE, "متأخر السداد"),
        (STATUS_CANCELLED, "ملغى"),
    ]

    organization = models.OneToOneField(
        "tenancy.Organization",
        on_delete=models.CASCADE,
        related_name="subscription",
        verbose_name="المؤسسة",
    )
    plan = models.CharField("الباقة", max_length=20, choices=Plan.choices, default=Plan.FREE)
    status = models.CharField("الحالة", max_length=20, choices=STATUS_CHOICES, default=STATUS_TRIAL)
    mrr = models.DecimalField(
        "الإيراد الشهري", max_digits=10, decimal_places=2, default=Decimal("0")
    )
    current_period_start = models.DateTimeField("بداية الدورة", default=timezone.now)
    current_period_end = models.DateTimeField("نهاية الدورة", db_index=True)
    gateway_ref = models.CharField("مرجع البوابة", max_length=120, blank=True)
    cancelled_at = models.DateTimeField("تاريخ الإلغاء", null=True, blank=True)

    class Meta:
        verbose_name = "اشتراك"
        verbose_name_plural = "الاشتراكات"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.organization.name} — {self.get_plan_display()}"

    @property
    def limits(self) -> dict:
        return PLAN_LIMITS[self.plan]

    @property
    def is_serving(self) -> bool:
        """
        هل يُخدَم هذا الاشتراك؟

        المتأخر سدادًا يُخدَم عمدًا: قطع الخدمة عن متجر لأن فاتورته
        تأخرت يومًا يعني عميلًا واقفًا عند الصندوق لا يحصل على نقاطه.
        الإيقاف قرار بشري لا آلي.
        """
        return self.status != self.STATUS_CANCELLED

    def limit(self, key: str):
        return self.limits.get(key)


class Invoice(BaseModel):
    """فاتورة دورة اشتراك."""

    STATUS_DRAFT = "draft"
    STATUS_ISSUED = "issued"
    STATUS_PAID = "paid"
    STATUS_VOID = "void"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "مسودة"),
        (STATUS_ISSUED, "صادرة"),
        (STATUS_PAID, "مدفوعة"),
        (STATUS_VOID, "ملغاة"),
    ]

    subscription = models.ForeignKey(
        Subscription, on_delete=models.PROTECT, related_name="invoices", verbose_name="الاشتراك"
    )
    number = models.CharField("الرقم", max_length=30, unique=True)
    amount = models.DecimalField("القيمة", max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(
        "الضريبة", max_digits=10, decimal_places=2, default=Decimal("0")
    )
    status = models.CharField(
        "الحالة", max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True
    )
    period_start = models.DateTimeField("من")
    period_end = models.DateTimeField("إلى")
    issued_at = models.DateTimeField("تاريخ الإصدار", null=True, blank=True)
    paid_at = models.DateTimeField("تاريخ السداد", null=True, blank=True)
    payment_ref = models.CharField("مرجع السداد", max_length=120, blank=True)
    pdf_url = models.URLField("ملف PDF", blank=True)

    class Meta:
        verbose_name = "فاتورة"
        verbose_name_plural = "الفواتير"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.number} — {self.total}"

    @property
    def total(self) -> Decimal:
        return self.amount + self.tax_amount


class MessageCredit(AppendOnlyModel):
    """
    حركة على رصيد الرسائل — append-only كقيود الولاء.

    نفس المنطق: التاجر يدفع مقابل هذا الرصيد، فيجب أن يكون كل خصم
    قابلًا للتفسير. اللقطة في `MessageWallet`.
    """

    REASON_TOPUP = "topup"
    REASON_MONTHLY = "monthly_grant"
    REASON_SEND = "send"
    REASON_REFUND = "refund"
    REASON_ADJUST = "adjust"
    REASON_CHOICES = [
        (REASON_TOPUP, "شحن"),
        (REASON_MONTHLY, "منحة شهرية"),
        (REASON_SEND, "إرسال"),
        (REASON_REFUND, "استرداد"),
        (REASON_ADJUST, "تسوية"),
    ]

    organization = models.ForeignKey(
        "tenancy.Organization",
        on_delete=models.PROTECT,
        related_name="message_credits",
        verbose_name="المؤسسة",
    )
    delta = models.IntegerField("المقدار")
    reason = models.CharField("السبب", max_length=20, choices=REASON_CHOICES)
    balance_after = models.IntegerField("الرصيد بعده")
    note = models.CharField("ملاحظة", max_length=200, blank=True)

    class Meta:
        verbose_name = "حركة رصيد رسائل"
        verbose_name_plural = "حركات رصيد الرسائل"
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["organization", "-created_at"], name="credit_org_time_idx")]
        constraints = [
            models.CheckConstraint(condition=~models.Q(delta=0), name="credit_delta_not_zero")
        ]

    def __str__(self) -> str:
        sign = "+" if self.delta > 0 else ""
        return f"{sign}{self.delta} ({self.get_reason_display()})"


class MessageWallet(BaseModel):
    """لقطة رصيد الرسائل — مصدر الحقيقة هو MessageCredit."""

    organization = models.OneToOneField(
        "tenancy.Organization",
        on_delete=models.CASCADE,
        related_name="message_wallet",
        verbose_name="المؤسسة",
    )
    balance = models.IntegerField("الرصيد", default=0)

    class Meta:
        verbose_name = "محفظة رسائل"
        verbose_name_plural = "محافظ الرسائل"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(balance__gte=0), name="message_wallet_not_negative"
            )
        ]

    def __str__(self) -> str:
        return f"{self.organization.name} — {self.balance} رسالة"
