from django.urls import path

from . import views

app_name = "fraud"

urlpatterns = [
    path("merchant/fraud-signals", views.FraudSignalListView.as_view(), name="signals"),
    path(
        "merchant/fraud-signals/<uuid:pk>/resolve",
        views.FraudSignalResolveView.as_view(),
        name="resolve",
    ),
]
