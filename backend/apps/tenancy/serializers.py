from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from apps.accounts.validators import normalize_phone

from .models import Branch, Brand, StaffUser, Terminal

User = get_user_model()


class BrandSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = Brand
        fields = (
            "id",
            "name",
            "slug",
            "category",
            "primary_color",
            "logo",
            "is_active",
            "tagline",
            "organization_name",
            "created_at",
        )
        read_only_fields = ("id", "slug", "is_active", "created_at")
        # المؤسسة والمعرّف لا يُعدَّلان من لوحة التاجر: الأول يخص
        # التعاقد، والثاني يظهر في روابط منشورة
        read_only_fields = ("id", "slug", "organization_name")


class BranchSerializer(serializers.ModelSerializer):
    terminals_count = serializers.IntegerField(source="terminals.count", read_only=True)
    staff_count = serializers.IntegerField(source="staff.count", read_only=True)

    class Meta:
        model = Branch
        fields = (
            "id",
            "name",
            "address",
            "lat",
            "lng",
            "opening_hours",
            "is_active",
            "terminals_count",
            "staff_count",
        )
        read_only_fields = ("id", "terminals_count", "staff_count")


class TerminalSerializer(serializers.ModelSerializer):
    branch_id = serializers.UUIDField(write_only=True, required=False)
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = Terminal
        fields = (
            "id",
            "label",
            "is_active",
            "branch_id",
            "branch_name",
            "code_expires_at",
        )
        # الرمز الحالي لا يُعرض هنا: شاشة الكاشير وحدها تعرضه، وعرضه
        # في قائمة إدارية يعني إمكان مسحه من بعيد
        read_only_fields = ("id", "branch_name", "code_expires_at")


class StaffUserSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(source="user.phone", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = StaffUser
        fields = ("id", "phone", "full_name", "role", "branch_name", "is_active")
        read_only_fields = fields


class StaffUserWriteSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    full_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=StaffUser.ROLE_CHOICES)
    branch_id = serializers.UUIDField()
    password = serializers.CharField(
        max_length=128, required=False, allow_blank=True, write_only=True
    )

    def validate_phone(self, value):
        return normalize_phone(value)

    @transaction.atomic
    def create(self, validated_data):
        brand = validated_data.pop("brand")
        branch = Branch.objects.get(pk=validated_data["branch_id"], brand=brand)

        user = User.objects.filter(phone=validated_data["phone"]).first()
        if user is None:
            user = User.objects.create_user(
                phone=validated_data["phone"],
                password=validated_data.get("password") or None,
                full_name=validated_data.get("full_name", ""),
            )

        record, created = StaffUser.objects.get_or_create(
            user=user,
            branch=branch,
            defaults={"role": validated_data["role"]},
        )
        if not created:
            # الموظف موجود في هذا الفرع: يُعاد تفعيله بدوره الجديد
            # بدل رفض الطلب برسالة لا يفهمها المالك
            record.role = validated_data["role"]
            record.is_active = True
            record.save(update_fields=["role", "is_active", "updated_at"])

        return record
