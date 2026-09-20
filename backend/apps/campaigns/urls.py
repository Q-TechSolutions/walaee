from django.urls import path

from . import views

app_name = "campaigns"

urlpatterns = [
    path("merchant/campaigns", views.CampaignListView.as_view(), name="campaigns"),
    path("merchant/campaigns/preview", views.CampaignPreviewView.as_view(), name="preview"),
    path("merchant/campaigns/<uuid:pk>", views.CampaignDetailView.as_view(), name="campaign"),
    path("merchant/campaigns/<uuid:pk>/send", views.CampaignSendView.as_view(), name="send"),
    path("merchant/campaigns/<uuid:pk>/cancel", views.CampaignCancelView.as_view(), name="cancel"),
]
