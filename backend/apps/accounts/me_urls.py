"""مسارات حساب العميل — تُركَّب على /api/v1/ مباشرة."""

from django.urls import path

from . import me_views

app_name = "me"

urlpatterns = [
    path("me", me_views.MeView.as_view(), name="profile"),
    path("me/summary", me_views.MyBalancesSummaryView.as_view(), name="summary"),
    path("me/cards", me_views.MyCardsView.as_view(), name="cards"),
    path("me/cards/<uuid:brand_id>", me_views.CardDetailView.as_view(), name="card"),
    path("me/activity", me_views.MyActivityView.as_view(), name="activity"),
    path("me/redemptions", me_views.MyRedemptionsView.as_view(), name="redemptions"),
    path("me/notifications", me_views.MyNotificationsView.as_view(), name="notifications"),
    path("me/transactions/<uuid:pk>", me_views.MyTransactionView.as_view(), name="transaction"),
    path("me/push-subscription", me_views.PushSubscriptionView.as_view(), name="push"),
    path("me/export", me_views.ExportMyDataView.as_view(), name="export"),
    path("me/delete", me_views.DeleteAccountView.as_view(), name="delete"),
    path("stores/nearby", me_views.NearbyStoresView.as_view(), name="nearby"),
]
