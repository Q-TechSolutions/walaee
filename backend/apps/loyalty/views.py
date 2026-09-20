"""
إدارة البرامج والقواعد والمكافآت والعملاء من لوحة التاجر.

تعديل قاعدة برنامج يؤثر على المنح **من لحظته فقط** — القيود السابقة
لا تُعاد حسابتها أبدًا. عميل جمع نقاطه بمعدل قديم يحتفظ بها كما هي،
وإلا تغيّر رصيد عملاء بأثر رجعي بلا أن يفعلوا شيئًا.
"""

from django.db import transaction
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing import services as billing
from apps.common.pagination import DefaultPagination
from apps.pos.permissions import IsManager, IsOwner, get_staff_user

from .models import LoyaltyProgram, Membership, Reward
from .serializers import (
    CustomerDetailSerializer,
    MembershipSerializer,
    ProgramRuleSerializer,
    ProgramSerializer,
    RewardWriteSerializer,
)


class ProgramListView(APIView):
    permission_classes = [IsManager]

    @extend_schema(responses=ProgramSerializer(many=True), summary="برامج العلامة")
    def get(self, request):
        staff = get_staff_user(request)
        programs = (
            LoyaltyProgram.objects.filter(brand=staff.branch.brand)
            .select_related("rule")
            .order_by("name")
        )
        return Response(ProgramSerializer(programs, many=True).data)

    @extend_schema(request=ProgramSerializer, responses=ProgramSerializer, summary="إنشاء برنامج")
    @transaction.atomic
    def post(self, request):
        staff = get_staff_user(request)
        brand = staff.branch.brand

        billing.check_limit(
            brand.organization,
            "max_programs",
            LoyaltyProgram.objects.filter(brand=brand).count(),
        )

        serializer = ProgramSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(brand=brand)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ProgramRuleView(APIView):
    # تعديل القواعد للمالك: هي ما يحدّد تكلفة البرنامج عليه
    permission_classes = [IsOwner]

    @extend_schema(
        request=ProgramRuleSerializer,
        responses=ProgramRuleSerializer,
        summary="تعديل قواعد المنح والصلاحية",
    )
    def put(self, request, pk):
        staff = get_staff_user(request)
        program = LoyaltyProgram.objects.select_related("rule").get(pk=pk, brand=staff.branch.brand)

        serializer = ProgramRuleSerializer(program.rule, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                **serializer.data,
                "note": "التعديل يسري على المنح الجديدة فقط — القيود السابقة لا تتغيّر.",
            }
        )


class RewardListView(APIView):
    permission_classes = [IsManager]

    @extend_schema(responses=RewardWriteSerializer(many=True), summary="مكافآت العلامة")
    def get(self, request):
        staff = get_staff_user(request)
        rewards = (
            Reward.objects.filter(program__brand=staff.branch.brand)
            .select_related("program")
            .order_by("program__name", "cost_amount")
        )
        return Response(RewardWriteSerializer(rewards, many=True).data)

    @extend_schema(
        request=RewardWriteSerializer,
        responses=RewardWriteSerializer,
        summary="إضافة مكافأة",
    )
    def post(self, request):
        staff = get_staff_user(request)

        serializer = RewardWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        program = LoyaltyProgram.objects.get(
            pk=serializer.validated_data["program_id"], brand=staff.branch.brand
        )
        serializer.save(program=program)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class RewardDetailView(APIView):
    permission_classes = [IsManager]

    @extend_schema(
        request=RewardWriteSerializer,
        responses=RewardWriteSerializer,
        summary="تعديل مكافأة",
    )
    def patch(self, request, pk):
        staff = get_staff_user(request)
        reward = Reward.objects.get(pk=pk, program__brand=staff.branch.brand)

        serializer = RewardWriteSerializer(reward, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class MerchantCustomerListView(APIView):
    permission_classes = [IsManager]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="search", type=str, description="بحث بالهاتف أو الاسم"),
            OpenApiParameter(
                name="segment",
                type=str,
                description="active · dormant · new — شرائح جاهزة",
            ),
        ],
        responses=MembershipSerializer(many=True),
        summary="عملاء العلامة",
    )
    def get(self, request):
        staff = get_staff_user(request)

        queryset = (
            Membership.objects.filter(brand=staff.branch.brand, customer__deleted_at__isnull=True)
            .select_related("customer")
            .prefetch_related("balances__program")
            .order_by("-joined_at")
        )

        search = (request.query_params.get("search") or "").strip()
        if search:
            # البحث بالهاتف يطبّع أولًا: التاجر يكتب 010… والمخزَّن +2010…
            from apps.accounts.validators import normalize_phone

            try:
                normalized = normalize_phone(search)
            except Exception:  # noqa: BLE001 - نص بحث حر قد لا يكون رقمًا
                normalized = ""

            from django.db.models import Q

            condition = Q(customer__full_name__icontains=search)
            if normalized:
                condition |= Q(customer__phone__icontains=normalized)
            queryset = queryset.filter(condition)

        segment = request.query_params.get("segment")
        if segment:
            queryset = _apply_segment(queryset, segment)

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(MembershipSerializer(page, many=True).data)


def _apply_segment(queryset, segment: str):
    from datetime import timedelta

    from django.db.models import Max, Q
    from django.utils import timezone

    now = timezone.now()
    annotated = queryset.annotate(last_activity=Max("entries__created_at"))

    if segment == "active":
        return annotated.filter(last_activity__gte=now - timedelta(days=30))
    if segment == "dormant":
        cutoff = now - timedelta(days=90)
        return annotated.filter(Q(last_activity__lt=cutoff) | Q(last_activity__isnull=True))
    if segment == "new":
        return annotated.filter(joined_at__gte=now - timedelta(days=7))

    return annotated


class MerchantCustomerDetailView(APIView):
    permission_classes = [IsManager]

    @extend_schema(responses=CustomerDetailSerializer, summary="ملف عميل داخل العلامة")
    def get(self, request, pk):
        staff = get_staff_user(request)
        membership = (
            Membership.objects.select_related("customer")
            .prefetch_related("balances__program")
            .get(pk=pk, brand=staff.branch.brand)
        )
        return Response(CustomerDetailSerializer(membership).data)
