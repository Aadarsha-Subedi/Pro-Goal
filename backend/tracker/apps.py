from django.apps import AppConfig


class TrackerConfig(AppConfig):
    name = "tracker"

    def ready(self) -> None:
        from projects.services import hooks, reassignment
        from tracker.services import reassignment as tracker_reassignment
        from tracker.services import seeding

        if seeding.seed_project_defaults not in hooks.project_created:
            hooks.project_created.append(seeding.seed_project_defaults)
        from tracker.services import copy as tracker_copy

        if tracker_copy.copy_content not in hooks.project_copied:
            hooks.project_copied.append(tracker_copy.copy_content)
        tracker_reassignment.register(reassignment.registry)
