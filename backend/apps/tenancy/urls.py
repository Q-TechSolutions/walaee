from django.urls import path

from . import views

app_name = "tenancy"

urlpatterns = [
    path("merchant/brand", views.BrandView.as_view(), name="brand"),
    path("merchant/branches", views.BranchListView.as_view(), name="branches"),
    path("merchant/branches/<uuid:pk>", views.BranchDetailView.as_view(), name="branch"),
    path("merchant/terminals", views.TerminalListView.as_view(), name="terminals"),
    path("merchant/staff", views.StaffListView.as_view(), name="staff"),
    path("merchant/staff/<uuid:pk>", views.StaffDetailView.as_view(), name="staff-detail"),
]
