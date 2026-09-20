"""
نظام الولاء: البرامج الستة وقواعدها والعضويات والأرصدة والمكافآت.

المرجع: docs/architecture/data-model.md — القسم ٢
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.common.models import BaseModel


class LoyaltyProgram(BaseModel):
    """
    برنامج ولاء واحد للعلامة.

    علامة واحدة قد تُشغّل أكثر من برنامج معًا — مثلًا نقاط على كل فاتورة
    وأختام على منتج بعينه. لذلك العلاقة 1—N لا 1—1.
    """

    TYPE_POINTS = "points"
    TYPE_STAMPS = "stamps"
    TYPE_VISITS = "visits"
    TYPE_CASHBACK = "cashback"
    TYPE_REWARDS = "rewards"
    TYPE_GIFTS = "gifts"
    TYPE_CHOICES = [
        (TYPE_POINTS, "نقاط"),
        (TYPE_STAMPS, "أختام"),
        (TYPE_VISITS, "زيارات"),
        (TYPE_CASHBACK, "استرداد نقدي"),
        (TYPE_REWARDS, "مكافآت"),
        (TYPE_GIFTS, "هدايا"),
    ]

    brand = models.ForeignKey(
        "tenancy.Brand",
        on_delete=models.CASCADE,
        related_name="programs",
        verbose_name="العلامة",
    )
    type = models.CharField("النموذج", max_length=20, choices=TYPE_CHOICES)
    name = models.CharField("الاسم", max_length=120)
    is_active = models.BooleanField("نشط", default=True)
    starts_at = models.DateTimeField("يبدأ", null=True, blank=True)
    ends_at = models.DateTimeField("ينتهي", null=True, blank=True)

    class Meta:
        verbose_name = "برنامج ولاء"
        verbose_name_plural = "برامج الولاء"
        ordering = ("brand__name", "name")

    def __str__(self) -> str:
        return f"{self.brand.name} — {self.name}"

    @property
    def unit_label(self) -> str:
        return {
            self.TYPE_POINTS: "نقطة",
            self.TYPE_STAMPS: "ختم",
            self.TYPE_VISITS: "زيارة",
            self.TYPE_CASHBACK: "جنيه",
            self.TYPE_REWARDS: "نقطة",
            self.TYPE_GIFTS: "هدية",
        }.get(self.type, "وحدة")


class ProgramRule(BaseModel):
    """
    قواعد المنح والصلاحية — سجل واحد لكل برنامج.

    `max_per_day` يغلق باب الاحتيال الداخلي (كاشير يمنح نفسه نقاطًا)
    و `expiry_months` يمنع تراكم التزام مفتوح على التاجر إلى الأبد.
    """

    REVERSAL_ALLOW = "allow"
    REVERSAL_MANAGER = "manager_only"
    REVERSAL_DENY = "deny"
    REVERSAL_CHOICES = [
        (REVERSAL_ALLOW, "مسموح للكاشير"),
        (REVERSAL_MANAGER, "المدير فقط"),
        (REVERSAL_DENY, "ممنوع"),
    ]

    program = models.OneToOneField(
        LoyaltyProgram,
        on_delete=models.CASCADE,
        related_name="rule",
        verbose_name="البرنامج",
    )
    earn_rate = models.DecimalField(
        "معدل المنح",
        max_digits=8,
        decimal_places=4,
        default=Decimal("1"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="نقاط لكل جنيه · أو ختم لكل فاتورة مؤهّلة",
    )
    min_invoice = models.DecimalField(
        "أقل فاتورة مؤهّلة",
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    max_per_day = models.DecimalField(
        "السقف اليومي",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="أقصى ما يُمنح للعميل الواحد في اليوم. فارغ = بلا سقف.",
    )
    expiry_months = models.PositiveSmallIntegerField("صلاحية الرصيد بالأشهر", null=True, blank=True)
    reversal_policy = models.CharField(
        "سياسة العكس", max_length=20, choices=REVERSAL_CHOICES, default=REVERSAL_MANAGER
    )
    welcome_bonus = models.PositiveIntegerField("مكافأة الانضمام", default=0)

    class Meta:
        verbose_name = "قاعدة برنامج"
        verbose_name_plural = "قواعد البرامج"

    def __str__(self) -> str:
        return f"قواعد {self.program.name}"


class Membership(BaseModel):
    """
    عضوية عميل في علامة.

    هذا الجدول هو ما يجعل الرصيد منفصلًا لكل علامة. بدونه تتحوّل
    المنصة إلى نظام مقاصة مالية بين التجّار — وهو منتج مختلف تمامًا
    له متطلبات تنظيمية لا نريدها.
    """

    STATUS_ACTIVE = "active"
    STATUS_BLOCKED = "blocked"
    STATUS_CHOICES = [(STATUS_ACTIVE, "نشطة"), (STATUS_BLOCKED, "محظورة")]

    customer = models.ForeignKey(
        "accounts.Customer",
        on_delete=models.PROTECT,
        related_name="memberships",
        verbose_name="العميل",
    )
    brand = models.ForeignKey(
        "tenancy.Brand",
        on_delete=models.PROTECT,
        related_name="memberships",
        verbose_name="العلامة",
    )
    joined_at = models.DateTimeField("تاريخ الانضمام", auto_now_add=True)
    status = models.CharField(
        "الحالة", max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE
    )
    tier = models.CharField("المستوى", max_length=40, blank=True)

    class Meta:
        verbose_name = "عضوية"
        verbose_name_plural = "العضويات"
        ordering = ("-joined_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "brand"], name="unique_membership_per_brand"
            )
        ]

    def __str__(self) -> str:
        return f"{self.customer} @ {self.brand.name}"


class Balance(BaseModel):
    """
    لقطة الرصيد.

    مصدر الحقيقة هو LedgerEntry لا هذا الجدول. وجوده للأداء فقط:
    جمع كل القيود عند كل قراءة رصيد غير عملي على مقياس الإنتاج.
    أي اختلاف بين الاثنين يعني خللًا يجب أن يُكشف — راجع
    `apps.ledger.services.verify_balance`.
    """

    membership = models.ForeignKey(
        Membership, on_delete=models.CASCADE, related_name="balances", verbose_name="العضوية"
    )
    program = models.ForeignKey(
        LoyaltyProgram, on_delete=models.CASCADE, related_name="balances", verbose_name="البرنامج"
    )
    amount = models.DecimalField("الرصيد", max_digits=12, decimal_places=2, default=Decimal("0"))
    expires_at = models.DateTimeField("ينتهي في", null=True, blank=True, db_index=True)

    class Meta:
        verbose_name = "رصيد"
        verbose_name_plural = "الأرصدة"
        constraints = [
            models.UniqueConstraint(
                fields=["membership", "program"], name="unique_balance_per_program"
            ),
            # الرصيد السالب مستحيل منطقيًا — الحارس على مستوى القاعدة
            # يكشف أي مسار يتجاوز apply_entry
            models.CheckConstraint(
                condition=models.Q(amount__gte=Decimal("0")),
                name="balance_never_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.membership} — {self.amount} {self.program.unit_label}"


class Reward(BaseModel):
    """
    مكافأة قابلة للاستبدال.

    `merchant_cost` هو ما يدفعه التاجر فعليًا، ويُستخدم في حساب
    «الالتزام القائم» — الرقم الذي يسأل عنه محاسب التاجر أولًا.
    """

    UNIT_POINTS = "points"
    UNIT_STAMPS = "stamps"
    UNIT_CHOICES = [(UNIT_POINTS, "نقاط"), (UNIT_STAMPS, "أختام")]

    program = models.ForeignKey(
        LoyaltyProgram, on_delete=models.CASCADE, related_name="rewards", verbose_name="البرنامج"
    )
    title = models.CharField("العنوان", max_length=140)
    description = models.TextField("الوصف", blank=True)
    cost_amount = models.DecimalField(
        "التكلفة بالوحدات",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    cost_unit = models.CharField("الوحدة", max_length=20, choices=UNIT_CHOICES, default=UNIT_POINTS)
    merchant_cost = models.DecimalField(
        "تكلفتها على التاجر", max_digits=10, decimal_places=2, default=Decimal("0")
    )
    stock = models.IntegerField("المخزون", null=True, blank=True, help_text="فارغ = بلا حد")
    is_active = models.BooleanField("نشطة", default=True)

    class Meta:
        verbose_name = "مكافأة"
        verbose_name_plural = "المكافآت"
        ordering = ("cost_amount",)

    def __str__(self) -> str:
        return self.title

    @property
    def in_stock(self) -> bool:
        return self.stock is None or self.stock > 0
