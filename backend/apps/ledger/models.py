"""
القيود والعمليات — القلب المالي للمنصة.

`LedgerEntry` بنمط append-only: لا UPDATE ولا DELETE أبدًا. أي تصحيح
يتم بقيد عكسي جديد يشير إلى الأصل عبر `reverses`.

السبب ليس أكاديميًا: رقم «الالتزام القائم» الذي يراه محاسب التاجر
يجب أن يكون قابلًا للاشتقاق من سجل غير قابل للتلاعب. سجل يُعدَّل
لا يُدافَع عنه أمام مراجع.

المرجع: docs/architecture/data-model.md — القسم ٣
"""

from decimal import Decimal

from django.db import models

from apps.common.models import AppendOnlyModel, BaseModel


class Transaction(BaseModel):
    """
    عملية شراء.

    القيد الفريد على (terminal, invoice_no) هو الحارس ضد تسجيل نفس
    الفاتورة مرتين — سواء بخطأ بشري أو بضغطة مكرّرة على زر التأكيد.
    """

    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_REJECTED = "rejected"
    STATUS_REVERSED = "reversed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "معلّقة"),
        (STATUS_CONFIRMED, "مؤكّدة"),
        (STATUS_REJECTED, "مرفوضة"),
        (STATUS_REVERSED, "معكوسة"),
    ]

    terminal = models.ForeignKey(
        "tenancy.Terminal",
        on_delete=models.PROTECT,
        related_name="transactions",
        verbose_name="نقطة البيع",
    )
    staff_user = models.ForeignKey(
        "tenancy.StaffUser",
        on_delete=models.PROTECT,
        related_name="transactions",
        null=True,
        blank=True,
        verbose_name="الكاشير",
    )
    customer = models.ForeignKey(
        "accounts.Customer",
        on_delete=models.PROTECT,
        related_name="transactions",
        null=True,
        blank=True,
        verbose_name="العميل",
    )
    invoice_no = models.CharField("رقم الفاتورة", max_length=40)
    invoice_amount = models.DecimalField("قيمة الفاتورة", max_digits=12, decimal_places=2)
    code_used = models.CharField("الرمز المستخدم", max_length=12, blank=True)
    status = models.CharField(
        "الحالة", max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )
    confirmed_at = models.DateTimeField("وقت التأكيد", null=True, blank=True)

    class Meta:
        verbose_name = "عملية"
        verbose_name_plural = "العمليات"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["terminal", "invoice_no"], name="unique_invoice_per_terminal"
            )
        ]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="txn_status_time_idx"),
        ]

    def __str__(self) -> str:
        return f"فاتورة {self.invoice_no} — {self.invoice_amount}"

    @property
    def brand_id(self):
        return self.terminal.branch.brand_id


class LedgerEntry(AppendOnlyModel):
    """
    قيد رصيد — يُكتب ولا يُعدَّل ولا يُحذف.

    `balance_after` مخزّن عمدًا رغم كونه مشتقًّا: يسمح بإعادة بناء
    التاريخ والتحقق من سلامة السلسلة بلا إعادة جمع كل القيود.
    """

    REASON_EARN = "earn"
    REASON_REDEEM = "redeem"
    REASON_EXPIRE = "expire"
    REASON_REVERSE = "reverse"
    REASON_ADJUST = "adjust"
    REASON_WELCOME = "welcome"
    REASON_CHOICES = [
        (REASON_EARN, "منح"),
        (REASON_REDEEM, "استبدال"),
        (REASON_EXPIRE, "انتهاء صلاحية"),
        (REASON_REVERSE, "عكس"),
        (REASON_ADJUST, "تسوية"),
        (REASON_WELCOME, "مكافأة انضمام"),
    ]

    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.PROTECT,
        related_name="entries",
        null=True,
        blank=True,
        verbose_name="العملية",
    )
    membership = models.ForeignKey(
        "loyalty.Membership",
        on_delete=models.PROTECT,
        related_name="entries",
        verbose_name="العضوية",
    )
    program = models.ForeignKey(
        "loyalty.LoyaltyProgram",
        on_delete=models.PROTECT,
        related_name="entries",
        verbose_name="البرنامج",
    )
    delta = models.DecimalField("المقدار", max_digits=12, decimal_places=2)
    reason = models.CharField("السبب", max_length=20, choices=REASON_CHOICES)
    reverses = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="reversed_by",
        null=True,
        blank=True,
        verbose_name="يعكس القيد",
    )
    balance_after = models.DecimalField("الرصيد بعده", max_digits=12, decimal_places=2)
    actor_label = models.CharField("الفاعل", max_length=120, blank=True)

    class Meta:
        verbose_name = "قيد"
        verbose_name_plural = "القيود"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["membership", "program", "-created_at"], name="entry_wallet_idx"),
            models.Index(fields=["reason", "-created_at"], name="entry_reason_idx"),
        ]
        constraints = [
            # قيد بمقدار صفر لا معنى له ويلوّث السجل
            models.CheckConstraint(
                condition=~models.Q(delta=Decimal("0")), name="entry_delta_not_zero"
            ),
            # لا يُعكس القيد مرتين
            models.UniqueConstraint(
                fields=["reverses"],
                condition=models.Q(reverses__isnull=False),
                name="entry_reversed_once",
            ),
        ]

    def __str__(self) -> str:
        sign = "+" if self.delta > 0 else ""
        return f"{sign}{self.delta} ({self.get_reason_display()})"


class Redemption(BaseModel):
    """
    استبدال مكافأة.

    الكود صالح ١٥ دقيقة ومرة واحدة — المدة قصيرة عمدًا لأن كودًا
    مفتوحًا لأيام يصبح قابلًا للتداول خارج التطبيق.
    """

    STATUS_PENDING = "pending"
    STATUS_USED = "used"
    STATUS_EXPIRED = "expired"
    STATUS_CHOICES = [
        (STATUS_PENDING, "بانتظار الصرف"),
        (STATUS_USED, "مصروفة"),
        (STATUS_EXPIRED, "منتهية"),
    ]

    reward = models.ForeignKey(
        "loyalty.Reward",
        on_delete=models.PROTECT,
        related_name="redemptions",
        verbose_name="المكافأة",
    )
    membership = models.ForeignKey(
        "loyalty.Membership",
        on_delete=models.PROTECT,
        related_name="redemptions",
        verbose_name="العضوية",
    )
    ledger_entry = models.OneToOneField(
        LedgerEntry,
        on_delete=models.PROTECT,
        related_name="redemption",
        verbose_name="القيد",
    )
    code = models.CharField("الكود", max_length=10, unique=True)
    status = models.CharField(
        "الحالة", max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )
    expires_at = models.DateTimeField("ينتهي في", db_index=True)
    used_at = models.DateTimeField("وقت الصرف", null=True, blank=True)
    used_by_staff = models.ForeignKey(
        "tenancy.StaffUser",
        on_delete=models.PROTECT,
        related_name="redemptions_served",
        null=True,
        blank=True,
        verbose_name="صرفها",
    )

    class Meta:
        verbose_name = "استبدال"
        verbose_name_plural = "الاستبدالات"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.code} — {self.reward.title}"
