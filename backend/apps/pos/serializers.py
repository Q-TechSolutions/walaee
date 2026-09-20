from decimal import Decimal

from rest_framework import serializers

from apps.ledger.models import Redemption, Transaction
from apps.loyalty.models import Reward


class TerminalCodeSerializer(serializers.Serializer):
    terminal_id = serializers.UUIDField()
    label = serializers.CharField()
    code = serializers.CharField()


class ResolveCodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=12, trim_whitespace=True)


class TransactionCreateSerializer(serializers.Serializer):
    # المسار الممسوح يرسل code، والمسار اليدوي يرسل phone
    code = serializers.CharField(max_length=12, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    invoice_no = serializers.CharField(max_length=40)
    invoice_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01")
    )

    def validate(self, attrs):
        if not attrs.get("code") and not attrs.get("phone"):
            raise serializers.ValidationError("أرسل رمز نقطة البيع أو رقم هاتف العميل.")
        return attrs


class TransactionSerializer(serializers.ModelSerializer):
    customer_phone = serializers.CharField(source="customer.phone", read_only=True)
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)

    class Meta:
        model = Transaction
        fields = (
            "id",
            "invoice_no",
            "invoice_amount",
            "status",
            "customer_phone",
            "customer_name",
            "created_at",
            "confirmed_at",
        )
        read_only_fields = fields


class RewardSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source="program.brand.name", read_only=True)
    program_name = serializers.CharField(source="program.name", read_only=True)

    class Meta:
        model = Reward
        fields = (
            "id",
            "title",
            "description",
            "cost_amount",
            "cost_unit",
            "stock",
            "brand_name",
            "program_name",
        )


class RedeemRequestSerializer(serializers.Serializer):
    reward_id = serializers.UUIDField()


class RedemptionSerializer(serializers.ModelSerializer):
    reward_title = serializers.CharField(source="reward.title", read_only=True)

    class Meta:
        model = Redemption
        fields = ("id", "code", "status", "expires_at", "used_at", "reward_title")
        read_only_fields = fields
