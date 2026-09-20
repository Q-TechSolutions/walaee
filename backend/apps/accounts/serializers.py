from rest_framework import serializers

from .models import Customer
from .validators import normalize_phone


class PhoneField(serializers.CharField):
    """يطبّع الرقم عند الاستقبال فلا يصل أي رقم خام إلى طبقة الخدمات."""

    def to_internal_value(self, data):
        return normalize_phone(super().to_internal_value(data))


class OtpRequestSerializer(serializers.Serializer):
    phone = PhoneField(max_length=20)


class OtpVerifySerializer(serializers.Serializer):
    phone = PhoneField(max_length=20)
    code = serializers.CharField(max_length=10, trim_whitespace=True)
    consent_version = serializers.CharField(max_length=20, required=False, allow_blank=True)


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class CustomerSerializer(serializers.ModelSerializer):
    has_consent = serializers.BooleanField(read_only=True)

    class Meta:
        model = Customer
        fields = ("id", "phone", "full_name", "birth_date", "has_consent", "created_at")
        read_only_fields = ("id", "phone", "created_at")
