from decimal import Decimal

from rest_framework import serializers

from .models import Balance, LoyaltyProgram, Membership, ProgramRule, Reward


class ProgramRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgramRule
        fields = (
            "earn_rate",
            "min_invoice",
            "max_per_day",
            "expiry_months",
            "reversal_policy",
            "welcome_bonus",
        )


class ProgramSerializer(serializers.ModelSerializer):
    rule = ProgramRuleSerializer(read_only=True)
    unit_label = serializers.CharField(read_only=True)
    rewards_count = serializers.IntegerField(source="rewards.count", read_only=True)

    class Meta:
        model = LoyaltyProgram
        fields = (
            "id",
            "name",
            "type",
            "is_active",
            "starts_at",
            "ends_at",
            "unit_label",
            "rule",
            "rewards_count",
        )
        read_only_fields = ("id", "unit_label", "rule", "rewards_count")

    def create(self, validated_data):
        program = super().create(validated_data)
        # برنامج بلا قاعدة لا يمنح شيئًا ويبدو معطّلًا بلا سبب ظاهر
        ProgramRule.objects.create(program=program)
        program.refresh_from_db()
        return program


class RewardWriteSerializer(serializers.ModelSerializer):
    program_id = serializers.UUIDField(write_only=True, required=False)
    program_name = serializers.CharField(source="program.name", read_only=True)
    unit_label = serializers.CharField(source="program.unit_label", read_only=True)

    class Meta:
        model = Reward
        fields = (
            "id",
            "title",
            "description",
            "cost_amount",
            "cost_unit",
            "merchant_cost",
            "stock",
            "is_active",
            "program_id",
            "program_name",
            "unit_label",
        )
        read_only_fields = ("id", "program_name", "unit_label")


class BalanceSerializer(serializers.ModelSerializer):
    program_name = serializers.CharField(source="program.name", read_only=True)
    unit_label = serializers.CharField(source="program.unit_label", read_only=True)
    program_type = serializers.CharField(source="program.type", read_only=True)

    class Meta:
        model = Balance
        fields = (
            "program_id",
            "program_name",
            "program_type",
            "unit_label",
            "amount",
            "expires_at",
        )


class MembershipSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(source="customer.phone", read_only=True)
    full_name = serializers.CharField(source="customer.full_name", read_only=True)
    balances = BalanceSerializer(many=True, read_only=True)

    class Meta:
        model = Membership
        fields = ("id", "phone", "full_name", "status", "tier", "joined_at", "balances")
        read_only_fields = fields


class CustomerDetailSerializer(MembershipSerializer):
    recent_activity = serializers.SerializerMethodField()
    total_spend = serializers.SerializerMethodField()

    class Meta(MembershipSerializer.Meta):
        fields = MembershipSerializer.Meta.fields + ("recent_activity", "total_spend")
        read_only_fields = fields

    def get_recent_activity(self, membership) -> list[dict]:
        entries = membership.entries.select_related("program").order_by("-created_at")[:20]
        return [
            {
                "id": str(entry.id),
                "delta": str(entry.delta),
                "reason": entry.reason,
                "reason_label": entry.get_reason_display(),
                "program": entry.program.name,
                "balance_after": str(entry.balance_after),
                "created_at": entry.created_at.isoformat(),
            }
            for entry in entries
        ]

    def get_total_spend(self, membership) -> str:
        from decimal import Decimal

        from django.db.models import Sum

        from apps.ledger.models import Transaction

        # الإنفاق داخل هذه العلامة فقط — عزل بيانات العلامات يمنع
        # إظهار إنفاق العميل عند منافس
        total = Transaction.objects.filter(
            customer=membership.customer,
            terminal__branch__brand=membership.brand,
            status=Transaction.STATUS_CONFIRMED,
        ).aggregate(total=Sum("invoice_amount"))["total"]

        return str(total or Decimal("0"))


class ManualGrantSerializer(serializers.Serializer):
    """
    منح أو خصم يدوي.

    `amount` موجب يمنح وسالب يخصم — عمليةٌ واحدة لا اثنتان، لأن
    الخصم اليدوي (تصحيح خطأ كاشير) يحتاج نفس الضوابط تمامًا:
    نفس الصلاحية، ونفس السبب المكتوب، ونفس السقف.
    """

    #: سقف العملية الواحدة. الغرض منه الخطأ المطبعي لا سوء النية:
    #: صفر زائد يحوّل ٥٠٠ إلى ٥٠٠٠ ويصنع التزامًا بضغطة واحدة.
    MAX_ABS = Decimal("100000")

    membership_id = serializers.UUIDField()
    program_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    note = serializers.CharField(max_length=200, allow_blank=False, trim_whitespace=True)

    def validate_amount(self, value: Decimal) -> Decimal:
        if value == 0:
            raise serializers.ValidationError("المقدار صفر لا يكتب قيدًا.")
        if abs(value) > self.MAX_ABS:
            raise serializers.ValidationError(
                f"الحد الأقصى للعملية الواحدة {self.MAX_ABS:,.0f}. "
                "قسّمها أو راجع الرقم — هذا الحدّ موجود لالتقاط الصفر الزائد."
            )
        return value

    def validate_note(self, value: str) -> str:
        # سبب من كلمة واحدة («تصحيح») لا يفسّر شيئًا بعد شهر
        if len(value.strip()) < 4:
            raise serializers.ValidationError("اكتب سببًا مفهومًا — يظهر للعميل وفي سجل التدقيق.")
        return value.strip()


class ManualGrantResultSerializer(serializers.Serializer):
    entry_id = serializers.UUIDField()
    delta = serializers.DecimalField(max_digits=12, decimal_places=2)
    balance_after = serializers.DecimalField(max_digits=12, decimal_places=2)
    unit_label = serializers.CharField()
    note = serializers.CharField()
