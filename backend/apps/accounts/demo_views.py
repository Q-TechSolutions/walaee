"""
حسابات التجربة المعروضة للواجهات.

تُظهر شاشات الدخول قائمة الحسابات الجاهزة فيدخل المجرّب بضغطة
واحدة. بدونها عليه أن يعرف الأرقام وكلمات المرور من مكان آخر
ويكتبها يدويًا — وأول ما يحدث أن يُدخل رقم مدير المنصة في تطبيق
العميل فيفشل بلا أن يفهم لماذا.

**متى تعمل:** حين يُضبَط `DEMO_LOGIN_PHONES` (لعملاء التجربة) أو
`DEMO_STAFF_PASSWORD` (لموظفي التجربة). القيم الفارغة — وهي
الافتراضي — تجعل النقطة تردّ ٤٠٤ كأنها غير موجودة.

**لماذا كشف كلمة مرور عبر API مقبول هنا:** هذه ليست حسابات عملاء
بل حسابات عرض مُعلَنة عمدًا، ولا تُنشَأ إلا على نشر تجريبي يُشغَّل
فيه `demo_accounts`. على الإنتاج الحقيقي لا متغيّر مضبوط ولا حساب
موجود ولا نقطة تستجيب.
"""

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import demo

# الأدوار كما ينشئها أمر demo_accounts
STAFF_ACCOUNTS = [
    ("01000000000", "مدير المنصة", "platform_admin", "admin"),
    ("01000000001", "مالك المتجر", "owner", "merchant"),
    ("01000000002", "مدير الفرع", "manager", "merchant"),
    ("01000000003", "كاشير", "cashier", "merchant"),
]

CUSTOMER_NAMES = {
    "+201111111111": "سارة عبد الله",
    "+201222222222": "محمود حسن",
    "+201333333333": "نورهان سعيد",
}

# مسار كل تطبيق كما يخدمه nginx في الإنتاج. تُعاد إلى الواجهة
# لتستطيع شاشة الدخول أن تدلّ على مكان الحسابات التي لا تخصّها —
# بدلها يبقى المستخدم يجرّب حسابًا في التطبيق الخطأ.
# تُضبَط بـDEMO_APP_URLS حين تُخدَم التطبيقات على نطاقات منفصلة.
DEFAULT_APP_URLS = {
    "customer": "/",
    "merchant": "/merchant/",
    "admin": "/admin/",
}


def staff_password() -> str:
    return str(getattr(settings, "DEMO_STAFF_PASSWORD", "") or "")


def app_urls() -> dict:
    """
    مسار كل تطبيق.

    الإعداد بصيغة `customer=/,merchant=/merchant/,admin=/admin/`.
    أي مفتاح غير مذكور يأخذ الافتراضي، فلا يختفي رابط بسبب إعداد
    ناقص.
    """
    urls = dict(DEFAULT_APP_URLS)

    for entry in getattr(settings, "DEMO_APP_URLS", []) or []:
        key, _, value = str(entry).partition("=")
        key, value = key.strip(), value.strip()
        if key in urls and value:
            urls[key] = value

    return urls


def is_enabled() -> bool:
    return bool(demo.demo_phones()) or bool(staff_password())


class DemoAccountsView(APIView):
    """قائمة حسابات التجربة لهذا النشر."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        responses={200: None, 404: None},
        summary="حسابات التجربة — على النشر التجريبي وحده",
    )
    def get(self, request):
        if not is_enabled():
            # ٤٠٤ لا ٤٠٣: على الإنتاج يجب ألا يوجد أثر لوجود
            # هذه النقطة أصلًا
            return Response(status=status.HTTP_404_NOT_FOUND)

        password = staff_password()
        staff = (
            [
                {
                    "phone": phone,
                    "label": label,
                    "role": role,
                    "app": app,
                    "password": password,
                }
                for phone, label, role, app in STAFF_ACCOUNTS
            ]
            if password
            else []
        )

        customers = [
            {
                "phone": phone,
                "label": CUSTOMER_NAMES.get(phone, "عميل تجربة"),
                "app": "customer",
                "code": demo.demo_code(),
            }
            # مرتّبة لأن القائمة تُعرض للمستخدم، والترتيب العشوائي
            # يجعل الحساب يقفز مكانه بين كل تحديث
            for phone in sorted(demo.demo_phones())
        ]

        return Response(
            {
                "enabled": True,
                "staff": staff,
                "customers": customers,
                "apps": app_urls(),
                "notice": "حسابات عرض — لا تُستخدم على نشر حقيقي.",
            }
        )
