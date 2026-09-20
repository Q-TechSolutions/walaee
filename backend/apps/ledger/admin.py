from django.contrib import admin

from .models import LedgerEntry, Redemption, Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("invoice_no", "invoice_amount", "status", "terminal", "created_at")
    list_filter = ("status", "terminal__branch__brand")
    search_fields = ("invoice_no", "customer__phone")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "updated_at", "confirmed_at")


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    """للقراءة فقط — القيود append-only حتى من لوحة الإدارة."""

    list_display = ("created_at", "membership", "program", "delta", "reason", "balance_after")
    list_filter = ("reason", "program__brand")
    search_fields = ("membership__customer__phone",)
    date_hierarchy = "created_at"
    readonly_fields = [f.name for f in LedgerEntry._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Redemption)
class RedemptionAdmin(admin.ModelAdmin):
    list_display = ("code", "reward", "status", "expires_at", "used_at")
    list_filter = ("status", "reward__program__brand")
    search_fields = ("code",)
    readonly_fields = ("ledger_entry", "created_at", "updated_at")
