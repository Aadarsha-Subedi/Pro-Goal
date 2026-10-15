from unittest import mock

from cryptography.fernet import Fernet
from django.test import override_settings

from integrations.models import Integration
from integrations.providers import registry
from integrations.testing import FakeProvider
from tracker.tests.base import TrackerTestCase


class IntegrationTestCase(TrackerTestCase):
    """Owner + project + Bob (Contributor), a registered fake provider and one
    active "fake" integration installed by the owner."""

    TOKEN = "xoxb-super-secret-token"

    def setUp(self) -> None:
        self.key = Fernet.generate_key().decode()
        patcher = override_settings(INTEGRATION_ENCRYPTION_KEYS=[self.key])
        patcher.enable()
        self.addCleanup(patcher.disable)
        super().setUp()
        self.provider = FakeProvider()
        registry.register(self.provider)
        self.addCleanup(registry.unregister, "fake")
        self.integration = self.connect()

    def connect(
        self, installed_by_email: str | None = "owner@example.com"
    ) -> Integration:
        from accounts.models import User

        installer = (
            User.objects.get(email=installed_by_email) if installed_by_email else None
        )
        integration = Integration.objects.create(
            project_id=self.pid,
            provider="fake",
            installed_by=installer,
            external_workspace_id="W1",
            settings={"channel": "C1"},
        )
        integration.set_token(self.TOKEN)
        integration.save()
        return integration

    def integrations_url(self, path: str = "") -> str:
        return self.url(f"integrations/{path}")

    def run_dispatch(self) -> int:
        from integrations.services import dispatcher

        with self.captureOnCommitCallbacks(execute=True):
            return dispatcher.dispatch_batch()

    def scheduled(self):
        """Capture (delivery_id, eta) of every scheduled delivery instead of
        running it, so retry timing can be inspected."""
        return mock.patch("integrations.services.delivery._enqueue")
