"""
الحملات والرسائل.

القاعدة الحاكمة: **التكلفة تُعرض قبل الإرسال لا بعده.**
تاجر يضغط «إرسال» ثم يكتشف أنه دفع ألف جنيه هو تاجر يلغي اشتراكه،
مهما كانت الحملة ناجحة.

المرجع: docs/architecture/data-model.md — القسم ٤
"""

from decimal import Decimal

from django.db import models

from apps.common.models import BaseModel


class Channel(models.TextChoices):
    """
    القنوات مرتّبة بالتكلفة تصاعديًا.

    الترتيب هنا هو ترتيب المحاولة في الموجّه: push مجاني ويصل لمن
    ثبّت التطبيق، ثم whatsapp، ثم sms كملاذ أخير.
    """

    PUSH = "push", "إشعار التطبيق"
    WHATSAPP = "whatsapp", "واتساب"
    SMS = "sms", "رسالة نصية"


class Campaign(BaseModel):
    STATUS_DRAFT = "draft"
    STATUS_SCHEDULED = "scheduled"
    STATUS_SENDING = "sending"
    STATUS_SENT = "sent"
    STATUS_CANCELLED = "cancelled"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "مسودة"),
        (STATUS_SCHEDULED, "مجدولة"),
        (STATUS_SENDING, "قيد الإرسال"),
        (STATUS_SENT, "أُرسلت"),
        (STATUS_CANCELLED, "ملغاة"),
        (STATUS_FAILED, "فشلت"),
    ]

    brand = models.ForeignKey(
        "tenancy.Brand",
        on_delete=models.CASCADE,
        related_name="campaigns",
        verbose_name="العلامة",
    )
    created_by = models.ForeignKey(
        "tenancy.StaffUser",
        on_delete=models.PROTECT,
        related_name="campaigns",
        null=True,
        blank=True,
        verbose_name="أنشأها",
    )
    name = models.CharField("الاسم", max_length=140)
    message_template = models.TextField(
        "نص الرسالة",
        help_text="يدعم {name} و {balance} و {brand}",
    )
    segment_query = models.JSONField("شريحة المستهدفين", default=dict, blank=True)
    channel_priority = models.JSONField(
        "ترتيب القنوات", default=list, blank=True, help_text="افتراضيًا: push ← whatsapp ← sms"
    )
    status = models.CharField(
        "الحالة", max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True
    )
    scheduled_at = models.DateTimeField("موعد الإرسال", null=True, blank=True, db_index=True)
    started_at = models.DateTimeField("بدأ في", null=True, blank=True)
    finished_at = models.DateTimeField("انتهى في", null=True, blank=True)

    estimated_recipients = models.PositiveIntegerField("عدد المستهدفين المقدَّر", default=0)
    estimated_cost = models.DecimalField(
        "التكلفة المقدَّرة", max_digits=10, decimal_places=2, default=Decimal("0")
    )
    actual_cost = models.DecimalField(
        "التكلفة الفعلية", max_digits=10, decimal_places=2, default=Decimal("0")
    )

    class Meta:
        verbose_name = "حملة"
        verbose_name_plural = "الحملات"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return self.name

    @property
    def channels(self) -> list[str]:
        return self.channel_priority or [Channel.PUSH, Channel.WHATSAPP, Channel.SMS]

    @property
    def is_editable(self) -> bool:
        return self.status in (self.STATUS_DRAFT, self.STATUS_SCHEDULED)


class MessageJob(BaseModel):
    """
    رسالة واحدة لمستلم واحد بتكلفتها.

    السجل لكل رسالة لا لكل حملة: بدونه لا يستطيع التاجر معرفة لماذا
    كلّفته حملة ما كلّفته، ولا يستطيع النظام استرداد رصيد الفاشلة.
    """

    STATUS_QUEUED = "queued"
    STATUS_SENT = "sent"
    STATUS_DELIVERED = "delivered"
    STATUS_READ = "read"
    STATUS_FAILED = "failed"
    STATUS_SKIPPED = "skipped"
    STATUS_CHOICES = [
        (STATUS_QUEUED, "في الطابور"),
        (STATUS_SENT, "أُرسلت"),
        (STATUS_DELIVERED, "وصلت"),
        (STATUS_READ, "قُرئت"),
        (STATUS_FAILED, "فشلت"),
        (STATUS_SKIPPED, "تُخطّيت"),
    ]

    campaign = models.ForeignKey(
        Campaign, on_delete=models.CASCADE, related_name="jobs", verbose_name="الحملة"
    )
    customer = models.ForeignKey(
        "accounts.Customer",
        on_delete=models.PROTECT,
        related_name="message_jobs",
        verbose_name="العميل",
    )
    channel = models.CharField("القناة", max_length=20, choices=Channel.choices)
    status = models.CharField(
        "الحالة", max_length=20, choices=STATUS_CHOICES, default=STATUS_QUEUED, db_index=True
    )
    cost = models.DecimalField("التكلفة", max_digits=8, decimal_places=4, default=Decimal("0"))
    provider_msg_id = models.CharField("مرجع المزوّد", max_length=120, blank=True)
    error = models.CharField("سبب الفشل", max_length=255, blank=True)
    sent_at = models.DateTimeField("وقت الإرسال", null=True, blank=True)

    class Meta:
        verbose_name = "رسالة"
        verbose_name_plural = "الرسائل"
        ordering = ("-created_at",)
        constraints = [
            # مستلم واحد مرة واحدة في الحملة الواحدة — يمنع الإرسال
            # المكرر عند إعادة تشغيل مهمة فشلت في منتصفها
            models.UniqueConstraint(
                fields=["campaign", "customer"], name="unique_recipient_per_campaign"
            )
        ]
        indexes = [
            models.Index(fields=["campaign", "status"], name="job_campaign_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.customer} — {self.get_channel_display()}"
