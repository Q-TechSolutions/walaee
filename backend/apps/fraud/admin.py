from django.contrib import admin

from .models import FraudSignal


@admin.register(FraudSignal)
class FraudSignalAdmin(admin.ModelAdmin):
    list_display = ("rule_code", "severity", "status", "transaction", "created_at")
    list_filter = ("severity", "status", "rule_code")
    readonly_fields = ("transaction", "rule_code", "details", "created_at")
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False
