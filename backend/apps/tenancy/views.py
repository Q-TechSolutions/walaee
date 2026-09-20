"""
حوكمة العلامة: الفروع ونقاط البيع والموظفون.

كلها للمالك وحده. مدير يستطيع إنشاء كاشير يعني أن حدّ الباقة
وكشف الاحتيال كليهما قابلان للالتفاف من داخل الفرع.

حدود الباقة تُفحص عند الإنشاء لا عند القراءة — المرجع:
apps/billing/services.check_limit
"""

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing import services as billing
from apps.pos.permissions import IsOwner, get_staff_user

from .models import Branch, StaffUser, Terminal
from .serializers import (
    BranchSerializer,
    BrandSerializer,
    StaffUserSerializer,
    StaffUserWriteSerializer,
    TerminalSerializer,
)


class BrandView(APIView):
    permission_classes = [IsOwner]

    @extend_schema(responses=BrandSerializer, summary="بيانات العلامة")
    def get(self, request):
        staff = get_staff_user(request)
        return Response(BrandSerializer(staff.branch.brand).data)

    @extend_schema(request=BrandSerializer, responses=BrandSerializer, summary="تعديل العلامة")
    def patch(self, request):
        staff = get_staff_user(request)
        serializer = BrandSerializer(staff.branch.brand, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class BranchListView(APIView):
    permission_classes = [IsOwner]

    @extend_schema(responses=BranchSerializer(many=True), summary="فروع العلامة")
    def get(self, request):
        staff = get_staff_user(request)
        branches = Branch.objects.filter(brand=staff.branch.brand).order_by("name")
        return Response(BranchSerializer(branches, many=True).data)

    @extend_schema(request=BranchSerializer, responses=BranchSerializer, summary="إضافة فرع")
    @transaction.atomic
    def post(self, request):
        staff = get_staff_user(request)
        brand = staff.branch.brand

        billing.check_limit(
            brand.organization, "max_branches", Branch.objects.filter(brand=brand).count()
        )

        serializer = BranchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(brand=brand)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BranchDetailView(APIView):
    permission_classes = [IsOwner]

    @extend_schema(request=BranchSerializer, responses=BranchSerializer, summary="تعديل فرع")
    def patch(self, request, pk):
        staff = get_staff_user(request)
        branch = Branch.objects.get(pk=pk, brand=staff.branch.brand)

        serializer = BranchSerializer(branch, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class TerminalListView(APIView):
    permission_classes = [IsOwner]

    @extend_schema(responses=TerminalSerializer(many=True), summary="نقاط البيع")
    def get(self, request):
        staff = get_staff_user(request)
        terminals = (
            Terminal.objects.filter(branch__brand=staff.branch.brand)
            .select_related("branch")
            .order_by("branch__name", "label")
        )
        return Response(TerminalSerializer(terminals, many=True).data)

    @extend_schema(
        request=TerminalSerializer, responses=TerminalSerializer, summary="إضافة نقطة بيع"
    )
    @transaction.atomic
    def post(self, request):
        staff = get_staff_user(request)
        brand = staff.branch.brand

        billing.check_limit(
            brand.organization,
            "max_terminals",
            Terminal.objects.filter(branch__brand=brand).count(),
        )

        serializer = TerminalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        branch = Branch.objects.get(pk=serializer.validated_data["branch_id"], brand=brand)
        serializer.save(branch=branch)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class StaffListView(APIView):
    permission_classes = [IsOwner]

    @extend_schema(responses=StaffUserSerializer(many=True), summary="الموظفون")
    def get(self, request):
        staff = get_staff_user(request)
        people = (
            StaffUser.objects.filter(branch__brand=staff.branch.brand)
            .select_related("user", "branch")
            .order_by("branch__name", "role")
        )
        return Response(StaffUserSerializer(people, many=True).data)

    @extend_schema(
        request=StaffUserWriteSerializer,
        responses=StaffUserSerializer,
        summary="إضافة موظف",
    )
    @transaction.atomic
    def post(self, request):
        staff = get_staff_user(request)
        brand = staff.branch.brand

        billing.check_limit(
            brand.organization,
            "max_staff",
            StaffUser.objects.filter(branch__brand=brand).count(),
        )

        serializer = StaffUserWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = serializer.save(brand=brand)

        return Response(StaffUserSerializer(record).data, status=status.HTTP_201_CREATED)


class StaffDetailView(APIView):
    permission_classes = [IsOwner]

    @extend_schema(responses={200: None}, summary="تعطيل موظف")
    def delete(self, request, pk):
        staff = get_staff_user(request)
        person = StaffUser.objects.get(pk=pk, branch__brand=staff.branch.brand)

        if person.pk == staff.pk:
            return Response(
                {
                    "error": {
                        "code": "cannot_disable_self",
                        "message": "لا يمكنك تعطيل حسابك أنت.",
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )

        # التعطيل لا الحذف: الموظف مرتبط بعمليات وقيود، وحذفه يجعل
        # تاريخها غير قابل للنسبة إلى أحد
        person.is_active = False
        person.save(update_fields=["is_active", "updated_at"])

        return Response({"id": str(person.id), "is_active": False})
