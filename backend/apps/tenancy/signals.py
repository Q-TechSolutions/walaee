"""
إبطال ذاكرة الدليل العام.

الدليل مخزَّن خمس دقائق. بلا هذا الملف يفتتح تاجر فرعًا جديدًا من
لوحته ثم لا يراه على الخريطة، فيعيد إنشاءه ظنًّا أن الحفظ فشل —
والنتيجة فرعان متطابقان يتقاسمان عملاء الحي.

الإبطال على `post_save` لا على `pre_save`: الصف يجب أن يكون في
القاعدة قبل أن يُسمح لأول طلب بإعادة البناء، وإلا أعاد بناء
الدليل من حالة ما قبل التغيير وخزّنها خمس دقائق أخرى.
"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Branch, Brand
from .public_views import invalidate_network_cache


@receiver(post_save, sender=Brand)
@receiver(post_delete, sender=Brand)
@receiver(post_save, sender=Branch)
@receiver(post_delete, sender=Branch)
def _refresh_directory(sender, **kwargs) -> None:
    invalidate_network_cache()
