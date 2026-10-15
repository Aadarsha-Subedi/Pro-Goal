from django.core.management.base import BaseCommand
from django.db import transaction

from projects.services import demo_service
from projects.services.demo_data import DEMO_PROJECTS
from tracker.services import demo_seed


class Command(BaseCommand):
    help = (
        "Create the shared demo projects and their system owner. Safe to run "
        "again: existing projects are left alone unless --refresh is given."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Rebuild the tasks and notes of existing demo projects.",
        )
        parser.add_argument(
            "--join-existing",
            action="store_true",
            help="Also join every existing account to the demo projects.",
        )

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        for spec in DEMO_PROJECTS:
            project, created = demo_service.get_or_create_demo_project(spec)
            if created or options["refresh"]:
                demo_seed.seed_content(project, spec)
            state = (
                "created" if created else "refreshed" if options["refresh"] else "kept"
            )
            self.stdout.write(f"{spec['key']}: {state}")
        if options["join_existing"]:
            from accounts.models import User

            users = User.visible.filter(is_system=False, is_active=True)
            for user in users:
                demo_service.join_all_demo_projects(user)
            self.stdout.write(f"joined {users.count()} accounts")
