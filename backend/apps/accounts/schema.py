"""
تعريف مخطط المصادقة لـ OpenAPI.

بدون هذا الامتداد لا يعرف drf-spectacular كيف يصف
`WalaeeJWTAuthentication`، فيُولَّد مخطط بلا أي نظام أمان —
وأي عميل يُولَّد منه لا يرسل رأس المصادقة أصلًا.
"""

from drf_spectacular.extensions import OpenApiAuthenticationExtension


class WalaeeJWTScheme(OpenApiAuthenticationExtension):
    target_class = "apps.accounts.authentication.WalaeeJWTAuthentication"
    name = "BearerJWT"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "توكن وصول من `/auth/otp/verify` لعملاء التطبيق، "
                "أو من مسار دخول الموظفين. صالح ١٥ دقيقة."
            ),
        }
