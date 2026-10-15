from django.contrib import admin

from projects.models import Membership, Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "task_key", "owner", "is_deleted", "created_at")
    search_fields = ("name", "task_key")

    def get_queryset(self, request):
        return Project.all_objects.all()


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("project", "user", "is_owner", "joined_at")
