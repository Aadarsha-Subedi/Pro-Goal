from collections.abc import Callable

from projects.models import Project

# Features register a callable run inside the transaction that creates a
# project (tracker seeds its default statuses and priorities this way).
ProjectCreatedHook = Callable[[Project], None]
project_created: list[ProjectCreatedHook] = []


def run_project_created(project: Project) -> None:
    for hook in project_created:
        hook(project)


# Run for each project about to be permanently deleted, before its rows go
# (integrations revoke their provider tokens here).
ProjectPurgingHook = Callable[[Project], None]
project_purging: list[ProjectPurgingHook] = []


def run_project_purging(project: Project) -> None:
    for hook in project_purging:
        hook(project)


# Run inside the transaction that copies a demo project, after the new project
# exists: (source, copy). Tracker clones statuses, tasks, notes and comments.
ProjectCopiedHook = Callable[[Project, Project], None]
project_copied: list[ProjectCopiedHook] = []


def run_project_copied(source: Project, copy: Project) -> None:
    for hook in project_copied:
        hook(source, copy)
