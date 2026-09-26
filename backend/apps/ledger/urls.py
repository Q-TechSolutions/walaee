from django.urls import path

from . import views

app_name = "ledger"

urlpatterns = [
    path("merchant/dashboard", views.MerchantDashboardView.as_view(), name="dashboard"),
    path("merchant/series", views.MerchantSeriesView.as_view(), name="series"),
    path("merchant/activity", views.MerchantActivityView.as_view(), name="activity"),
    path("merchant/shift", views.CashierShiftView.as_view(), name="shift"),
    path("merchant/liability", views.MerchantLiabilityView.as_view(), name="liability"),
    path("merchant/segments", views.MerchantSegmentsView.as_view(), name="segments"),
    path("merchant/insights", views.MerchantInsightsView.as_view(), name="insights"),
    path("merchant/reports/<str:kind>", views.MerchantReportView.as_view(), name="report"),
    path("merchant/entries/<uuid:pk>/reverse", views.ReverseEntryView.as_view(), name="reverse"),
]
