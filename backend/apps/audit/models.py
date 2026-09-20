"""
سجل التدقيق — من فعل ماذا ومتى ومن أين.

السجل append-only كالقيود. الحماية الحقيقية على مستوى صلاحيات
PostgreSQL في infra/postgres/ — REVOKE UPDATE, DELETE على الجدول.
يُحفظ ٢٤ شهرًا ثم يُؤرشَف.

المرجع: docs/architecture/security.md
"""

from django.db import models

from apps.common.models import AppendOnlyModel

from .context import get_audit_context


class AuditLog(AppendOnlyModel):
    ACTOR_STAFF = "staff"
    ACTOR_CUSTOMER = "customer"
    ACTOR_SYSTEM = "system"
    ACTOR_CHOICES = [
        (ACTOR_STAFF, "موظف"),
        (ACTOR_CUSTOMER, "عميل"),
        (ACTOR_SYSTEM, "النظام"),
    ]

    actor_type = models.CharField(
        "نوع الفاعل", max_length=20, choices=ACTOR_CHOICES, default=ACTOR_SYSTEM
    )
    actor_id = models.CharField("معرّف الفاعل", max_length=64, blank=True)
    actor_label = models.CharField("اسم الفاعل", max_length=120, blank=True)

    action = models.CharField("الإجراء", max_length=80, db_index=True)
    entity_type = models.CharField("نوع الكيان", max_length=80, blank=True)
    entity_id = models.CharField("معرّف الكيان", max_length=64, blank=True)

    before = models.JSONField("قبل", null=True, blank=True)
    after = models.JSONField("بعد", null=True, blank=True)

    ip = models.GenericIPAddressField("العنوان", null=True, blank=True)
    user_agent = models.CharField("المتصفح", max_length=255, blank=True)

    class Meta:
        verbose_name = "سجل تدقيق"
        verbose_name_plural = "سجل التدقيق"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["entity_type", "entity_id"], name="audit_entity_idx"),
            models.Index(fields=["action", "-created_at"], name="audit_action_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.action} · {self.actor_label or self.actor_type}"

    @classmethod
    def record(cls, *, action: str, actor=None, entity=None, before=None, after=None):
        """
        يكتب سجلًا.

        IP والمتصفح يأتيان من سياق الطلب الجاري عبر middleware، فلا
        تحتاج كل طبقة خدمة أن تمرّر `request` إلى أعماق منطق الأعمال.
        """
        ctx = get_audit_context()

        actor_type = cls.ACTOR_SYSTEM
        actor_id = ""
        actor_label = ""
        if actor is not None:
            actor_id = str(getattr(actor, "id", "") or "")
            actor_label = str(actor)
            actor_type = (
                cls.ACTOR_CUSTOMER if type(actor).__name__ == "Customer" else cls.ACTOR_STAFF
            )

        return cls.objects.create(
            actor_type=actor_type,
            actor_id=actor_id,
            actor_label=actor_label[:120],
            action=action,
            entity_type=type(entity).__name__ if entity is not None else "",
            entity_id=str(getattr(entity, "id", "") or ""),
            before=before,
            after=after,
            ip=ctx.get("ip"),
            user_agent=(ctx.get("user_agent") or "")[:255],
        )
