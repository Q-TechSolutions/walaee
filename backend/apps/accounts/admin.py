from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Customer, OtpCode, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("-date_joined",)
    list_display = ("phone", "full_name", "is_platform_admin", "is_staff", "is_active")
    list_filter = ("is_active", "is_staff", "is_platform_admin")
    search_fields = ("phone", "full_name", "email")
    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("البيانات", {"fields": ("full_name", "email")}),
        (
            "الصلاحيات",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_platform_admin",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("التواريخ", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("phone", "password1", "password2")}),)
    readonly_fields = ("date_joined", "last_login")


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("phone", "full_name", "has_consent", "created_at", "deleted_at")
    list_filter = ("deleted_at",)
    search_fields = ("phone", "full_name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(OtpCode)
class OtpCodeAdmin(admin.ModelAdmin):
    # الكود مُجزّأ ولا يُعرض — الجدول للتدقيق لا للاطلاع على الأكواد
    list_display = ("phone", "purpose", "expires_at", "consumed_at", "attempts")
    list_filter = ("purpose",)
    search_fields = ("phone",)
    readonly_fields = [f.name for f in OtpCode._meta.fields]

    def has_add_permission(self, request):
        return False
