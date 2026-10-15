from django.contrib import admin

from attachments.models import Attachment, ProjectStorageUsage, UserStorageUsage


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ("filename", "project", "uploaded_by", "size_bytes", "status")
    list_filter = ("status", "category")
    readonly_fields = ("object_key",)


@admin.register(ProjectStorageUsage)
class ProjectStorageUsageAdmin(admin.ModelAdmin):
    list_display = ("project", "bytes_used", "quota_bytes")


@admin.register(UserStorageUsage)
class UserStorageUsageAdmin(admin.ModelAdmin):
    list_display = ("user", "bytes_used", "quota_bytes")
