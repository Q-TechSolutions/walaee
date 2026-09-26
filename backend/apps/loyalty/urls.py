from django.urls import path

from . import views

app_name = "loyalty"

urlpatterns = [
    path("merchant/programs", views.ProgramListView.as_view(), name="programs"),
    path("merchant/programs/<uuid:pk>/rule", views.ProgramRuleView.as_view(), name="program-rule"),
    path("merchant/rewards", views.RewardListView.as_view(), name="rewards"),
    path("merchant/rewards/<uuid:pk>", views.RewardDetailView.as_view(), name="reward"),
    path("merchant/customers", views.MerchantCustomerListView.as_view(), name="customers"),
    path(
        "merchant/customers/<uuid:pk>", views.MerchantCustomerDetailView.as_view(), name="customer"
    ),
    path("merchant/grant", views.ManualGrantView.as_view(), name="grant"),
]
