from django.urls import path

from .views import OtpRequestView, OtpVerifyView

app_name = "accounts"

urlpatterns = [
    path("otp/request", OtpRequestView.as_view(), name="otp-request"),
    path("otp/verify", OtpVerifyView.as_view(), name="otp-verify"),
]
