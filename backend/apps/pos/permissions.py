"""
صلاحيات نقطة البيع.

الدور يُقرأ من StaffUser لا من User: نفس الشخص قد يكون مالكًا لعلامة
وكاشيرًا في فرع آخر، والصلاحية تتبع الموقع لا الهوية.
"""

from django.contrib.auth import get_user_model
from rest_framework.permissions import BasePermission

from apps.accounts.models import Customer
from apps.tenancy.models import StaffUser

User = get_user_model()


def get_staff_user(request) -> StaffUser | None:
    """
    يجلب سجل الموظف للمستخدم الحالي ويخزّنه على الطلب.

    التخزين يمنع استعلامًا مكرّرًا في كل فحص صلاحية داخل نفس الطلب.
    """
    # العميل قد يكون هو صاحب الطلب — والاستعلام عنه كموظف خطأ نوعي
    if not isinstance(getattr(request, "user", None), User):
        return None

    cached = getattr(request, "_staff_user", None)
    if cached is not None:
        return cached

    staff = (
        StaffUser.objects.select_related("branch__brand", "user")
        .filter(user=request.user, is_active=True)
        .first()
    )
    request._staff_user = staff
    return staff


class IsCashier(BasePermission):
    message = "هذه العملية متاحة لموظفي نقطة البيع فقط."

    def has_permission(self, request, view):
        return get_staff_user(request) is not None


class IsManager(BasePermission):
    message = "هذه العملية متاحة للمدير أو المالك."

    def has_permission(self, request, view):
        staff = get_staff_user(request)
        return staff is not None and staff.can_view_reports


class IsOwner(BasePermission):
    message = "هذه العملية متاحة لمالك العلامة فقط."

    def has_permission(self, request, view):
        staff = get_staff_user(request)
        return staff is not None and staff.can_manage_brand


class IsCustomer(BasePermission):
    """
    توكن عميل لا توكن موظف.

    يميّزهما ادّعاء `scope` داخل التوكن — راجع
    apps.accounts.services.issue_tokens_for_customer
    """

    message = "هذه العملية متاحة لعملاء التطبيق."

    def has_permission(self, request, view):
        return isinstance(getattr(request, "user", None), Customer)
