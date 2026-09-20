"""
نقاط المصادقة.

الـView يستقبل ويتحقق ويستدعي الخدمة — لا منطق أعمال هنا.
"""

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .serializers import (
    CustomerSerializer,
    OtpRequestSerializer,
    OtpVerifySerializer,
    StaffLoginSerializer,
    TokenPairSerializer,
    TokenRefreshSerializer,
)
from .throttles import OtpIpThrottle, OtpPhoneThrottle, StaffLoginThrottle


def _client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class OtpRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OtpPhoneThrottle, OtpIpThrottle]

    @extend_schema(
        request=OtpRequestSerializer,
        responses={200: None},
        summary="طلب كود تحقق",
        description="محدود بـ ٣ محاولات لكل رقم و ١٠ لكل IP خلال ١٥ دقيقة.",
    )
    def post(self, request):
        serializer = OtpRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        services.request_otp(phone=serializer.validated_data["phone"], ip=_client_ip(request))

        # لا يُكشف أبدًا ما إذا كان الرقم مسجّلًا — تعداد الحسابات ثغرة خصوصية
        payload = {
            "sent": True,
            "expires_in": settings.OTP_TTL_SECONDS,
        }
        return Response(payload, status=status.HTTP_200_OK)


class OtpVerifyView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=OtpVerifySerializer,
        responses={200: TokenPairSerializer},
        summary="تأكيد الكود وإصدار JWT",
    )
    def post(self, request):
        serializer = OtpVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        customer, created = services.login_customer(
            phone=data["phone"],
            code=data["code"],
            consent_version=data.get("consent_version", ""),
        )
        tokens = services.issue_tokens_for_customer(customer)

        return Response(
            {
                **tokens,
                "is_new": created,
                "customer": CustomerSerializer(customer).data,
            },
            status=status.HTTP_200_OK,
        )


class StaffLoginView(APIView):
    """
    دخول الموظفين بالهاتف وكلمة المرور.

    منفصل عن دخول العملاء: الموظف يدخل من جهاز ثابت في المتجر عدة
    مرات يوميًا، وإرسال رسالة في كل مرة تكلفة بلا فائدة. العميل
    يدخل من هاتفه ولا كلمة مرور له أصلًا.
    """

    permission_classes = [AllowAny]
    throttle_classes = [StaffLoginThrottle]

    @extend_schema(
        request=StaffLoginSerializer,
        responses={200: TokenPairSerializer},
        summary="دخول موظف",
    )
    def post(self, request):
        serializer = StaffLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        result = services.login_staff(phone=data["phone"], password=data["password"])
        return Response(result, status=status.HTTP_200_OK)


class TokenRefreshView(APIView):
    """
    تجديد توكن الوصول.

    يعمل لهويتَي الموظف والعميل: يقرأ `scope` من توكن التحديث
    ويعيد بناء الوصول بنفس الادّعاءات.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        request=TokenRefreshSerializer,
        responses={200: TokenPairSerializer},
        summary="تجديد توكن الوصول",
    )
    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response(
            services.refresh_tokens(serializer.validated_data["refresh"]),
            status=status.HTTP_200_OK,
        )
