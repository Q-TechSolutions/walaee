from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "apps.accounts"
    label = "accounts"
    verbose_name = "الحسابات والمصادقة"

    def ready(self):
        # الاستيراد يسجّل امتداد مخطط المصادقة لدى drf-spectacular
        from . import schema  # noqa: F401
