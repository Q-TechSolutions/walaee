from django.urls import path

from . import views

app_name = "pos"

urlpatterns = [
    # ── شاشة الكاشير ──────────────────────────────
    path("pos/code", views.TerminalCodeView.as_view(), name="terminal-code"),
    path("pos/code/rotate", views.TerminalCodeView.as_view(), name="terminal-code-rotate"),
    path("pos/pending", views.PendingTransactionsView.as_view(), name="pending"),
    path(
        "pos/transactions/<uuid:pk>/confirm",
        views.ConfirmTransactionView.as_view(),
        name="confirm",
    ),
    path("pos/manual", views.ManualTransactionView.as_view(), name="manual"),
    path(
        "pos/redemptions/<str:code>/use",
        views.UseRedemptionView.as_view(),
        name="use-redemption",
    ),
    # ── تطبيق العميل ──────────────────────────────
    path("scan/resolve", views.ResolveCodeView.as_view(), name="scan-resolve"),
    path("transactions", views.CreateTransactionView.as_view(), name="create-transaction"),
    path("me/rewards", views.MyRewardsView.as_view(), name="my-rewards"),
    path("redemptions", views.RedeemView.as_view(), name="redeem"),
]
