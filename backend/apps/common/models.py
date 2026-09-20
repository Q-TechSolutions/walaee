"""
النماذج القاعدية التي ترث منها كل جداول المشروع.

قرار مُلزِم: المفاتيح الأساسية uuid لا أعداد متسلسلة.
السبب أن معرّفات العمليات والقيود تظهر في روابط وأكواد يراها التاجر،
والعدّاد المتسلسل يكشف حجم النشاط لأي طرف خارجي.
"""

import uuid

from django.db import models
from django.utils import timezone


class UUIDModel(models.Model):
    """مفتاح أساسي uuid4."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    """طابعا الإنشاء والتحديث."""

    created_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BaseModel(UUIDModel, TimeStampedModel):
    """الأساس المشترك: uuid + طوابع زمنية."""

    class Meta:
        abstract = True


class AppendOnlyModel(BaseModel):
    """
    نموذج لا يُعدَّل ولا يُحذف بعد الإنشاء.

    يمنع الخطأ البرمجي العرضي على مستوى بايثون. الحماية الحقيقية على
    مستوى قاعدة البيانات في infra/postgres/ — صلاحيات تمنع UPDATE و DELETE.
    """

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self._state.adding is False:
            raise AppendOnlyViolation(
                f"{type(self).__name__} بنمط append-only — التصحيح بقيد عكسي لا بتعديل."
            )
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise AppendOnlyViolation(f"{type(self).__name__} بنمط append-only — الحذف ممنوع نهائيًا.")


class AppendOnlyViolation(Exception):
    """محاولة تعديل أو حذف سجل append-only."""


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(deleted_at__isnull=True)


class SoftDeleteModel(BaseModel):
    """
    حذف ناعم.

    حق العميل في الحذف يصطدم بقاعدة «القيود لا تُحذف». الحل المعتمد:
    تُحذف بيانات الهوية وتبقى القيود بمعرّف مجهول — docs/architecture/security.md
    """

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteQuerySet.as_manager()

    class Meta:
        abstract = True

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
