from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    name = "projects"

    def ready(self) -> None:
        from accounts.services import deletion_service
        from projects.models import Project

        def owns_a_project(user) -> bool:
            # Projects scheduled for deletion still block until they are purged.
            return Project.all_objects.filter(owner=user).exists()

        if owns_a_project not in deletion_service.ownership_checks:
            deletion_service.ownership_checks.append(owns_a_project)

        from accounts.services import hooks as account_hooks
        from projects.services import demo_service

        if demo_service.join_all_demo_projects not in account_hooks.user_activated:
            account_hooks.user_activated.append(demo_service.join_all_demo_projects)
