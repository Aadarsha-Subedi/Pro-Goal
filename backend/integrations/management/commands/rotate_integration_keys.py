from django.core.management.base import BaseCommand

from integrations import crypto
from integrations.models import Integration, LinkedAccount


class Command(BaseCommand):
    help = (
        "Re-encrypt every stored provider token with the first key in "
        "PROJECT_MANAGEMENT_INTEGRATION_ENCRYPTION_KEYS. Put the new key first, "
        "run this, then remove the old key."
    )

    def handle(self, *args, **options) -> None:
        rotated = 0
        for model in (Integration, LinkedAccount):
            for row in model.objects.exclude(encrypted_token=""):
                row.encrypted_token = crypto.rotate(row.encrypted_token)
                row.save(update_fields=["encrypted_token"])
                rotated += 1
        self.stdout.write(f"Re-encrypted {rotated} tokens.")
