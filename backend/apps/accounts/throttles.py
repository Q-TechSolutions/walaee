"""
تحديد معدل طلب OTP.

الحد مزدوج عمدًا: الرقم وحده يمنع إغراق عميل بعينه برسائل، و IP
وحده يمنع مهاجمًا يجرّب أرقامًا كثيرة من مصدر واحد.

لماذا نافذة صريحة بدل صيغة DRF؟
`SimpleRateThrottle` يقرأ وحدة المدة من **أول حرف** فقط
(`{'s','m','h','d'}[period[0]]`)، فصيغة مثل `"3/15m"` تُفسَّر على أن
المدة `"1"` وترفع `KeyError` عند أول طلب. أي أن المتطلب الأمني
«٣ محاولات لكل ١٥ دقيقة» غير قابل للتعبير عنه بصيغة DRF أصلًا —
لذلك تُضبَط `num_requests` و `duration` مباشرة.

المرجع: docs/architecture/security.md
"""

from rest_framework.throttling import SimpleRateThrottle


class WindowThrottle(SimpleRateThrottle):
    """عدد طلبات محدّد خلال نافذة بالثواني."""

    num_requests = 3
    duration = 15 * 60

    def __init__(self):
        # لا يُستدعى super: مُهيّئ الأصل يحلّل صيغة `rate` التي لا
        # تستطيع تمثيل نافذتنا. القيمة هنا للتوثيق وللفحص ضد None
        # داخل `allow_request` فقط.
        self.rate = f"{self.num_requests}/{self.duration}s"

    def get_cache_key(self, request, view):  # pragma: no cover - يُعاد تعريفه
        raise NotImplementedError


class OtpPhoneThrottle(WindowThrottle):
    """٣ محاولات لكل رقم خلال ١٥ دقيقة."""

    scope = "otp_phone"
    num_requests = 3
    duration = 15 * 60

    def get_cache_key(self, request, view):
        phone = (request.data or {}).get("phone")
        if not phone:
            return None

        # أرقام التجربة معفاة: كودها ثابت ومعلَن أصلًا، فالحد لا
        # يحمي شيئًا ولا يوجد ما يُرسَل ليُغرَق به أحد. ما يفعله
        # فقط هو إيقاف من يعرض المنتج بعد ثلاث محاولات.
        # الإعفاء محصور فيها — كل رقم آخر يبقى محدودًا.
        from . import demo

        if demo.is_demo_phone(phone):
            return None

        return self.cache_format % {"scope": self.scope, "ident": phone}


class OtpIpThrottle(WindowThrottle):
    """١٠ محاولات لكل عنوان خلال ١٥ دقيقة — أوسع لأن الشبكات تشترك في IP."""

    scope = "otp_ip"
    num_requests = 10
    duration = 15 * 60

    def get_cache_key(self, request, view):
        # عرض المنتج يعني عدة حسابات تجربة من نفس الجهاز والشبكة،
        # فحدّ العنوان يوقفه بلا أن يحمي شيئًا
        from . import demo

        phone = (request.data or {}).get("phone")
        if phone and demo.is_demo_phone(phone):
            return None

        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class StaffLoginThrottle(WindowThrottle):
    """
    ١٠ محاولات دخول لكل رقم خلال ١٥ دقيقة.

    أوسع من OTP لأن الموظف يخطئ في كلمة مروره بشكل طبيعي، وأضيق
    بكثير من اللانهاية لأن حساب الكاشير يفتح باب تأكيد العمليات.
    """

    scope = "staff_login"
    num_requests = 10
    duration = 15 * 60

    def get_cache_key(self, request, view):
        phone = (request.data or {}).get("phone")
        if not phone:
            return None
        return self.cache_format % {"scope": self.scope, "ident": phone}
