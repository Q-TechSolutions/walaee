from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """للقراءة فقط — السجل append-only حتى من لوحة الإدارة."""

    list_display = ("created_at", "action", "actor_label", "entity_type", "ip")
    list_filter = ("actor_type", "action")
    search_fields = ("action", "actor_label", "entity_id")
    readonly_fields = [f.name for f in AuditLog._meta.fields]
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
