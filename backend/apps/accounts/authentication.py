"""
مصادقة تفهم هويتين في نفس الـAPI.

النظام فيه نوعان من الحسابات: `User` (أصحاب المتاجر والفريق) و
`Customer` (العميل النهائي). المصادقة الافتراضية في SimpleJWT تبحث
عن `User` بمعرّف التوكن دائمًا، فكانت توكنات العملاء تُرفَض قبل أن
تصل إلى فحص الصلاحيات أصلًا.

التمييز عبر ادّعاء `scope` داخل التوكن — راجع
`services.issue_tokens_for_customer`.
"""

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken

from .models import Customer

SCOPE_CUSTOMER = "customer"


class WalaeeJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        if validated_token.get("scope") == SCOPE_CUSTOMER:
            return self._get_customer(validated_token)
        return super().get_user(validated_token)

    def _get_customer(self, validated_token) -> Customer:
        try:
            customer_id = validated_token["user_id"]
        except KeyError as exc:
            raise InvalidToken("التوكن لا يحمل معرّف الحساب.") from exc

        customer = Customer.objects.filter(pk=customer_id, deleted_at__isnull=True).first()

        if customer is None:
            # حساب محذوف بتوكن ما زال صالحًا زمنيًا — يُرفض فورًا
            raise AuthenticationFailed("الحساب غير موجود أو محذوف.")

        return customer
