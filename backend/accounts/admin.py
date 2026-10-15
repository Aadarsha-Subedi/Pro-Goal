from django.contrib import admin

from accounts.models import User, UserSession


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "display_name",
        "is_active",
        "is_system",
        "is_deleted",
        "created_at",
    )
    list_filter = ("is_system",)
    search_fields = ("email", "display_name")
    exclude = ("password",)

    def get_readonly_fields(self, request, obj=None):
        return ("is_system",) if obj is not None else ()

    def has_delete_permission(self, request, obj=None):
        return not (obj is not None and obj.is_system)


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "device_name", "ip", "last_seen_at")
