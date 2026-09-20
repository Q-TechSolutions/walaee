from django.urls import path

from .demo_views import DemoAccountsView
from .views import OtpRequestView, OtpVerifyView, StaffLoginView, TokenRefreshView

app_name = "accounts"

urlpatterns = [
    path("otp/request", OtpRequestView.as_view(), name="otp-request"),
    path("otp/verify", OtpVerifyView.as_view(), name="otp-verify"),
    path("staff/login", StaffLoginView.as_view(), name="staff-login"),
    path("token/refresh", TokenRefreshView.as_view(), name="token-refresh"),
    # تردّ ٤٠٤ ما لم يُضبَط متغيّر تجربة — راجع demo_views.py
    path("demo-accounts", DemoAccountsView.as_view(), name="demo-accounts"),
]
