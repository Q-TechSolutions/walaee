"""مسارات لوحة إدارة المنصة."""

from django.urls import path

from . import admin_views

app_name = "platform"

urlpatterns = [
    path("overview", admin_views.PlatformOverviewView.as_view(), name="overview"),
    path("merchants", admin_views.PlatformMerchantsView.as_view(), name="merchants"),
    path("invoices", admin_views.PlatformInvoicesView.as_view(), name="invoices"),
    path(
        "invoices/<uuid:pk>/mark-paid",
        admin_views.PlatformMarkPaidView.as_view(),
        name="mark-paid",
    ),
]
