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


#: ترويسة اختيار الفرع التي ترسلها لوحة التاجر.
#:
#: الشخص الواحد قد يعمل في أكثر من فرع — بل في أكثر من علامة: مالك
#: يملك مقهى ومخبزًا، أو مدير منطقة يشرف على فرعين. بلا هذه
#: الترويسة كان الخادم يختار أولهما أبجديًا ويصمت، فلا يجد صاحب
#: العلامتين بابًا واحدًا إلى الثانية — بياناتها موجودة ولا سبيل
#: إليها من الواجهة إطلاقًا.
BRANCH_HEADER = "HTTP_X_WALAEE_BRANCH"


def staff_roles(user) -> list[StaffUser]:
    """كل أدوار المستخدم النشطة، بترتيب ثابت."""
    return list(
        StaffUser.objects.select_related("branch__brand", "user")
        .filter(user=user, is_active=True)
        .order_by("branch__brand__name", "branch__name")
    )


def get_staff_user(request) -> StaffUser | None:
    """
    يجلب سجل الموظف للمستخدم الحالي ويخزّنه على الطلب.

    التخزين يمنع استعلامًا مكرّرًا في كل فحص صلاحية داخل نفس الطلب.

    الفرع المطلوب يأتي من ترويسة العميل، **ويُتحقَّق منه دائمًا**
    مقابل أدوار هذا المستخدم هو. الترويسة اختيار لا إذن: من يزوّرها
    بمعرّف فرع لا يملك فيه دورًا لا يحصل على شيء، ويعود إلى دوره
    الأول كأنه لم يرسلها.
    """
    # العميل قد يكون هو صاحب الطلب — والاستعلام عنه كموظف خطأ نوعي
    if not isinstance(getattr(request, "user", None), User):
        return None

    cached = getattr(request, "_staff_user", None)
    if cached is not None:
        return cached

    roles = staff_roles(request.user)
    requested = (request.META.get(BRANCH_HEADER) or "").strip()

    staff = None
    if requested:
        staff = next((role for role in roles if str(role.branch_id) == requested), None)

    # لا فرع مطلوب أو مطلوب لا يملكه: الأول بالترتيب الثابت أعلاه
    if staff is None:
        staff = roles[0] if roles else None

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
