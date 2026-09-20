from django.contrib import admin

from .models import Branch, Brand, Organization, StaffUser, Terminal


class BranchInline(admin.TabularInline):
    model = Branch
    extra = 0
    fields = ("name", "address", "is_active")


class TerminalInline(admin.TabularInline):
    model = Terminal
    extra = 0
    fields = ("label", "is_active", "code_expires_at")
    readonly_fields = ("code_expires_at",)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "billing_email", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "legal_name", "tax_id")


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "category", "is_active")
    list_filter = ("is_active", "category")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [BranchInline]


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "brand", "is_active")
    list_filter = ("is_active", "brand")
    search_fields = ("name", "address")
    inlines = [TerminalInline]


@admin.register(Terminal)
class TerminalAdmin(admin.ModelAdmin):
    list_display = ("label", "branch", "is_active", "code_expires_at")
    list_filter = ("is_active", "branch__brand")
    readonly_fields = ("current_code", "code_expires_at")


@admin.register(StaffUser)
class StaffUserAdmin(admin.ModelAdmin):
    list_display = ("user", "branch", "role", "is_active")
    list_filter = ("role", "is_active", "branch__brand")
    search_fields = ("user__phone", "user__full_name")
