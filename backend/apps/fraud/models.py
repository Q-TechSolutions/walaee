"""
إشارات الشذوذ.

الإشارة ليست حكمًا. النظام لا يلغي عملية تلقائيًا أبدًا — يرفع راية
ويترك القرار للمالك. الإلغاء التلقائي لعملية صحيحة أمام عميل واقف
عند الصندوق أسوأ من احتيال بقيمة فاتورة واحدة.

المرجع: docs/architecture/data-model.md — القسم ٤
"""

from django.db import models

from apps.common.models import BaseModel


class FraudSignal(BaseModel):
    SEVERITY_LOW = "low"
    SEVERITY_MEDIUM = "medium"
    SEVERITY_HIGH = "high"
    SEVERITY_CHOICES = [
        (SEVERITY_LOW, "منخفضة"),
        (SEVERITY_MEDIUM, "متوسطة"),
        (SEVERITY_HIGH, "عالية"),
    ]

    STATUS_OPEN = "open"
    STATUS_ACCEPTED = "accepted"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_OPEN, "بانتظار المراجعة"),
        (STATUS_ACCEPTED, "مقبولة — العملية سليمة"),
        (STATUS_REJECTED, "مرفوضة — عُكست العملية"),
    ]

    transaction = models.ForeignKey(
        "ledger.Transaction",
        on_delete=models.CASCADE,
        related_name="fraud_signals",
        verbose_name="العملية",
    )
    rule_code = models.CharField("رمز القاعدة", max_length=40, db_index=True)
    severity = models.CharField(
        "الخطورة", max_length=10, choices=SEVERITY_CHOICES, default=SEVERITY_LOW
    )
    details = models.JSONField("التفاصيل", default=dict, blank=True)
    status = models.CharField(
        "الحالة", max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN, db_index=True
    )
    reviewed_by = models.ForeignKey(
        "tenancy.StaffUser",
        on_delete=models.PROTECT,
        related_name="fraud_reviews",
        null=True,
        blank=True,
        verbose_name="راجعها",
    )
    reviewed_at = models.DateTimeField("وقت المراجعة", null=True, blank=True)

    class Meta:
        verbose_name = "إشارة شذوذ"
        verbose_name_plural = "إشارات الشذوذ"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["transaction", "rule_code"], name="unique_signal_per_rule"
            )
        ]

    def __str__(self) -> str:
        return f"{self.rule_code} ({self.get_severity_display()})"
