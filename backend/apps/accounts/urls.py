from django.urls import path

from .views import OtpRequestView, OtpVerifyView, StaffLoginView, TokenRefreshView

app_name = "accounts"

urlpatterns = [
    path("otp/request", OtpRequestView.as_view(), name="otp-request"),
    path("otp/verify", OtpVerifyView.as_view(), name="otp-verify"),
    path("staff/login", StaffLoginView.as_view(), name="staff-login"),
    path("token/refresh", TokenRefreshView.as_view(), name="token-refresh"),
]
