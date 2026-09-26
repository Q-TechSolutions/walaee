from django.apps import AppConfig


class TenancyConfig(AppConfig):
    name = "apps.tenancy"
    label = "tenancy"
    verbose_name = "الهيكل التنظيمي"

    def ready(self):
        # الاستيراد داخل ready لا في أعلى الملف: الإشارات تستورد
        # النماذج، واستيرادها وقت تحميل الإعدادات يرمي
        # AppRegistryNotReady قبل أن يبدأ أي شيء.
        from . import signals  # noqa: F401
