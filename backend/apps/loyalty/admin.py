from django.contrib import admin

from .models import Balance, LoyaltyProgram, Membership, ProgramRule, Reward


class ProgramRuleInline(admin.StackedInline):
    model = ProgramRule
    extra = 0
    can_delete = False


class RewardInline(admin.TabularInline):
    model = Reward
    extra = 0
    fields = ("title", "cost_amount", "cost_unit", "merchant_cost", "stock", "is_active")


@admin.register(LoyaltyProgram)
class LoyaltyProgramAdmin(admin.ModelAdmin):
    list_display = ("name", "brand", "type", "is_active")
    list_filter = ("type", "is_active", "brand")
    inlines = [ProgramRuleInline, RewardInline]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("customer", "brand", "status", "tier", "joined_at")
    list_filter = ("status", "brand")
    search_fields = ("customer__phone", "customer__full_name")


@admin.register(Balance)
class BalanceAdmin(admin.ModelAdmin):
    """للقراءة فقط — الرصيد يُعدَّل من محرك القيود حصرًا."""

    list_display = ("membership", "program", "amount", "expires_at", "updated_at")
    list_filter = ("program__brand", "program__type")
    search_fields = ("membership__customer__phone",)
    readonly_fields = [f.name for f in Balance._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    list_display = ("title", "program", "cost_amount", "merchant_cost", "stock", "is_active")
    list_filter = ("is_active", "program__brand")
    search_fields = ("title",)
