"""
عزل بيانات العلامات.

الضابط مطبَّق على مستوى المدير الافتراضي لا داخل كل View، لأن
View واحد يُنسى يعني تسريب بيانات عملاء بين تاجرين — وهو أسوأ عطل
ممكن في منصة ولاء.

المرجع: docs/architecture/security.md
"""

from django.db import models


class BrandScopedQuerySet(models.QuerySet):
    """
    يوفّر `for_brand()` لكل نموذج يمكن الوصول منه إلى العلامة.

    `brand_path` يُعرَّف في النموذج عندما لا يكون الحقل اسمه `brand`
    مباشرة، مثل Branch حيث المسار `brand` و Terminal حيث `branch__brand`.
    """

    def for_brand(self, brand):
        path = getattr(self.model, "brand_path", "brand")
        return self.filter(**{path: brand})

    def for_staff(self, staff_user):
        """
        يقصر النتائج على نطاق الموظف.

        المالك يرى العلامة كاملة، والمدير والكاشير فرعهما فقط.
        """
        from .models import StaffUser

        if staff_user.role == StaffUser.ROLE_OWNER:
            return self.for_brand(staff_user.branch.brand)

        path = getattr(self.model, "branch_path", "branch")
        return self.filter(**{path: staff_user.branch})
