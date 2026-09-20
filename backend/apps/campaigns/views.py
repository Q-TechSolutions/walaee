"""
نقاط الحملات.

`preview` منفصلة عن `create` عمدًا: التاجر يعدّل الشريحة ويرى الرقم
يتغيّر قبل أن يلتزم بأي شيء. وهي أرخص من الإنشاء فلا تكتب صفًا.
"""

from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing import services as billing
from apps.common.exceptions import InvalidState
from apps.pos.permissions import IsManager, get_staff_user

from . import services
from .models import Campaign, MessageJob


class CampaignSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.user.full_name", read_only=True)
    sent_count = serializers.SerializerMethodField()
    failed_count = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = (
            "id",
            "name",
            "message_template",
            "segment_query",
            "channel_priority",
            "status",
            "scheduled_at",
            "started_at",
            "finished_at",
            "estimated_recipients",
            "estimated_cost",
            "actual_cost",
            "created_by_name",
            "sent_count",
            "failed_count",
            "created_at",
        )
        read_only_fields = fields

    def get_sent_count(self, campaign) -> int:
        return campaign.jobs.filter(status=MessageJob.STATUS_SENT).count()

    def get_failed_count(self, campaign) -> int:
        return campaign.jobs.filter(status=MessageJob.STATUS_FAILED).count()


class CampaignWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=140)
    message_template = serializers.CharField(max_length=1000)
    segment_query = serializers.JSONField(required=False, default=dict)
    channel_priority = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)


class PreviewSerializer(serializers.Serializer):
    segment_query = serializers.JSONField(required=False, default=dict)
    channel_priority = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )


class CampaignPreviewView(APIView):
    permission_classes = [IsManager]

    @extend_schema(
        request=PreviewSerializer,
        responses={200: None},
        summary="تقدير التكلفة قبل الإنشاء",
    )
    def post(self, request):
        staff = get_staff_user(request)

        serializer = PreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response(
            services.preview(
                staff.branch.brand,
                serializer.validated_data["segment_query"],
                serializer.validated_data["channel_priority"] or None,
            )
        )


class CampaignListView(APIView):
    permission_classes = [IsManager]

    @extend_schema(responses=CampaignSerializer(many=True), summary="حملات العلامة")
    def get(self, request):
        staff = get_staff_user(request)
        campaigns = (
            Campaign.objects.filter(brand=staff.branch.brand)
            .select_related("created_by__user")
            .order_by("-created_at")[:100]
        )
        return Response(CampaignSerializer(campaigns, many=True).data)

    @extend_schema(
        request=CampaignWriteSerializer,
        responses=CampaignSerializer,
        summary="إنشاء حملة — يُرجع التكلفة قبل الإرسال",
    )
    def post(self, request):
        staff = get_staff_user(request)

        serializer = CampaignWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        campaign, quote = services.create_campaign(
            brand=staff.branch.brand,
            staff_user=staff,
            name=data["name"],
            message_template=data["message_template"],
            segment_query=data["segment_query"],
            channel_priority=data["channel_priority"] or None,
            scheduled_at=data.get("scheduled_at"),
        )

        return Response(
            {
                **CampaignSerializer(campaign).data,
                "estimate": quote.as_dict(),
                "wallet_balance": billing.wallet_balance(staff.branch.brand.organization),
            },
            status=status.HTTP_201_CREATED,
        )


class CampaignDetailView(APIView):
    permission_classes = [IsManager]

    @extend_schema(responses=CampaignSerializer, summary="تفاصيل حملة")
    def get(self, request, pk):
        staff = get_staff_user(request)
        campaign = Campaign.objects.select_related("created_by__user").get(
            pk=pk, brand=staff.branch.brand
        )
        return Response(CampaignSerializer(campaign).data)


class CampaignSendView(APIView):
    permission_classes = [IsManager]

    @extend_schema(request=None, responses={200: None}, summary="إرسال الحملة الآن")
    def post(self, request, pk):
        staff = get_staff_user(request)
        campaign = Campaign.objects.get(pk=pk, brand=staff.branch.brand)

        if campaign.status == Campaign.STATUS_CANCELLED:
            raise InvalidState("هذه الحملة ملغاة.", code="cancelled")

        # الإرسال إلى الطابور لا تنفيذه في الطلب: حملة بآلاف الرسائل
        # تتجاوز مهلة أي وكيل عكسي
        from .tasks import send_campaign_task

        send_campaign_task.delay(str(campaign.id))

        return Response(
            {
                "id": str(campaign.id),
                "queued": True,
                "message": "بدأ الإرسال. تابع الحالة من صفحة الحملة.",
            }
        )


class CampaignCancelView(APIView):
    permission_classes = [IsManager]

    @extend_schema(request=None, responses=CampaignSerializer, summary="إلغاء حملة")
    def post(self, request, pk):
        staff = get_staff_user(request)
        Campaign.objects.get(pk=pk, brand=staff.branch.brand)

        campaign = services.cancel_campaign(pk, staff_user=staff)
        return Response(CampaignSerializer(campaign).data)
