from django.urls import path

from . import views

app_name = "billing"

urlpatterns = [
    path("merchant/subscription", views.SubscriptionView.as_view(), name="subscription"),
    path("merchant/invoices", views.InvoiceListView.as_view(), name="invoices"),
    path("merchant/invoices/<uuid:pk>/payment", views.InvoicePaymentView.as_view(), name="payment"),
    path("merchant/message-wallet", views.MessageWalletView.as_view(), name="wallet"),
]
