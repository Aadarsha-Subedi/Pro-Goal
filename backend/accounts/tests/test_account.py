from dataclasses import replace
from datetime import timedelta
from io import BytesIO
from unittest import mock
from urllib.parse import urlencode

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from PIL import Image

from accounts import tasks
from accounts.models import User, UserSession
from accounts.services import deletion_service, google_service
from accounts.tests.base import ApiTestCase
from common.exception.domain import AuthenticationDeniedException
from common.storage.memory import InMemoryStorage


def image_bytes(fmt: str = "PNG", size: tuple[int, int] = (800, 600)) -> bytes:
    out = BytesIO()
    Image.new("RGB", size, "red").save(out, format=fmt)
    return out.getvalue()


class FakeVerifier(google_service.GoogleTokenVerifier):
    def __init__(self, profile: google_service.GoogleProfile | None = None):
        self.profile = profile

    def verify(self, token: str) -> google_service.GoogleProfile:
        if self.profile is None:
            raise AuthenticationDeniedException(
                "bad", error_code="google_token_invalid"
            )
        return self.profile


def profile(**kw) -> google_service.GoogleProfile:
    base = {
        "sub": "g-1",
        "email": "ada@example.com",
        "email_verified": True,
        "first_name": "Ada",
        "last_name": "Lovelace",
        "name": "Ada L",
        "picture": "",
        "raw": {},
    }
    return google_service.GoogleProfile(**{**base, **kw})


class GoogleTests(ApiTestCase):
    def _login(self, prof, **kw):
        with mock.patch.object(
            google_service, "GoogleIdTokenVerifier", return_value=FakeVerifier(prof)
        ):
            return self.post("/api/auth/google/", {"id_token": "t", **kw})

    def _redirect(self, prof, *, state="n1.0", cookie="n1.0", nonce="n1"):
        self.client.cookies["pg_google_state"] = cookie
        body = urlencode(
            {"id_token": "t", "state": state, "authuser": "0", "prompt": "none"}
        )
        prof = prof and replace(prof, raw={"nonce": nonce})
        with mock.patch.object(
            google_service, "GoogleIdTokenVerifier", return_value=FakeVerifier(prof)
        ):
            return self.client.post(
                "/api/auth/google/redirect/",
                body,
                content_type="application/x-www-form-urlencoded",
            )

    def test_redirect_flow_signs_in_and_returns_to_app(self):
        response = self._redirect(profile())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/app")
        self.assertEqual(self.client.get("/api/me/").status_code, 200)

    def test_redirect_flow_state_mismatch_is_rejected(self):
        response = self._redirect(profile(), state="other.0")
        self.assertEqual(response["Location"], "/login?google_error=google_failed")
        self.assertFalse(User.objects.exists())

    def test_redirect_flow_wrong_nonce_is_rejected(self):
        response = self._redirect(profile(), nonce="someone-else")
        self.assertEqual(response["Location"], "/login?google_error=google_failed")
        self.assertFalse(User.objects.exists())

    def test_redirect_flow_invalid_token_returns_to_login(self):
        response = self._redirect(None)
        self.assertEqual(response["Location"], "/login?google_error=google_failed")

    def test_redirect_flow_honours_remember_flag_in_state(self):
        self._redirect(profile(), state="n1.1", cookie="n1.1")
        self.assertGreater(self.client.session.get_expiry_age(), 60 * 60 * 24)

    def test_new_user_created_verified_without_password(self):
        response = self._login(profile())
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(email="ada@example.com")
        self.assertFalse(user.has_usable_password())
        self.assertTrue(EmailAddress.objects.get(user=user).verified)
        self.assertTrue(SocialAccount.objects.filter(user=user, uid="g-1").exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_links_to_existing_account_when_google_verified(self):
        existing = self.make_user(verified=False)
        self._login(profile())
        self.assertTrue(SocialAccount.objects.filter(user=existing).exists())
        self.assertTrue(EmailAddress.objects.get(user=existing).verified)
        self.assertEqual(User.objects.count(), 1)

    def test_unverified_google_email_rejected(self):
        self.make_user()
        response = self._login(profile(email_verified=False))
        self.assertEqual(response.status_code, 401)
        self.assertFalse(SocialAccount.objects.exists())

    def test_invalid_token(self):
        self.assertEqual(self._login(None).status_code, 401)

    def test_incomplete_profile_blocks_until_completed(self):
        self._login(profile(first_name="", last_name=""))
        me = self.client.get("/api/me/")
        self.assertTrue(me.json()["data"]["needs_profile"])
        sessions = self.client.get("/api/me/sessions/")
        self.assertEqual(sessions.status_code, 200)  # account endpoints stay open
        self.patch("/api/me/", {"first_name": "Ada", "last_name": "L"})
        self.assertFalse(self.client.get("/api/me/").json()["data"]["needs_profile"])

    def test_profile_gate_permission(self):
        from rest_framework.test import APIRequestFactory

        from accounts.permissions import IsProfileComplete
        from common.exception.domain import PermissionDeniedException

        user = User.objects.create_user(
            "x@example.com", None, first_name="", last_name="", display_name="x"
        )
        request = APIRequestFactory().get("/")
        request.user = user
        with self.assertRaises(PermissionDeniedException) as ctx:
            IsProfileComplete().has_permission(request, None)
        self.assertEqual(ctx.exception.error_code, "profile_incomplete")

    @mock.patch("accounts.services.google_service.import_google_avatar")
    def test_avatar_import_queued_for_new_user(self, task):
        self._login(profile(picture="https://img.test/p.png"))
        task.delay.assert_called_once()


class ProfileTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.storage = InMemoryStorage()
        patcher = mock.patch(
            "accounts.services.avatar_service.get_storage", return_value=self.storage
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.user = self.make_user()
        self.login()

    def test_update_profile(self):
        response = self.patch("/api/me/", {"display_name": "Countess"})
        self.assertEqual(response.json()["data"]["display_name"], "Countess")

    def test_profile_rejects_unknown_and_email(self):
        self.assertEqual(
            self.patch("/api/me/", {"email": "x@example.com"}).status_code, 400
        )

    def _upload(self, content: bytes, name="a.png"):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(
                "/api/me/avatar/",
                {"file": SimpleUploadedFile(name, content)},
                format="multipart",
                **self._headers(),
            )

    def test_avatar_upload_resizes_and_stores_webp(self):
        response = self._upload(image_bytes("PNG"))
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        data, content_type = self.storage.objects[self.user.avatar]
        self.assertEqual(content_type, "image/webp")
        self.assertLessEqual(max(Image.open(BytesIO(data)).size), 512)

    def test_avatar_replaces_old_object(self):
        self._upload(image_bytes("PNG"))
        self.user.refresh_from_db()
        first = self.user.avatar
        self._upload(image_bytes("JPEG"))
        self.assertNotIn(first, self.storage.objects)
        self.assertEqual(len(self.storage.objects), 1)

    def test_avatar_rejects_gif_and_non_image_and_oversize(self):
        self.assertEqual(self._upload(image_bytes("GIF")).status_code, 400)
        self.assertEqual(self._upload(b"not an image").status_code, 400)
        with self.settings(AVATAR_MAX_BYTES=100):
            self.assertEqual(self._upload(image_bytes("PNG")).status_code, 400)


class SessionTests(ApiTestCase):
    def test_list_and_revoke(self):
        self.make_user()
        other = type(self.client)(
            enforce_csrf_checks=True, HTTP_USER_AGENT="Mozilla/5.0 (iPhone) Safari/604"
        )
        other.get("/api/csrf/")
        other.post(
            "/api/auth/login/",
            {"email": "ada@example.com", "password": "Correct-Horse-9"},
            format="json",
            HTTP_X_CSRFTOKEN=other.cookies["csrftoken"].value,
        )
        self.login()
        listing = self.client.get("/api/me/sessions/").json()["data"]["items"]
        self.assertEqual(len(listing), 2)
        self.assertEqual(sum(item["is_current"] for item in listing), 1)
        self.assertIn("Firefox on Linux", {item["device_name"] for item in listing})
        target = next(item for item in listing if not item["is_current"])
        self.assertEqual(
            self.delete(f"/api/me/sessions/{target['id']}/").status_code, 200
        )
        self.assertEqual(other.get("/api/me/").status_code, 401)
        self.assertEqual(
            self.delete(f"/api/me/sessions/{target['id']}/").status_code, 404
        )

    def test_cannot_revoke_someone_elses_session(self):
        self.make_user()
        stranger = self.make_user("b@example.com")
        foreign = UserSession.objects.create(
            user=stranger, session_key="x" * 32, last_seen_at=timezone.now()
        )
        self.login()
        self.assertEqual(
            self.delete(f"/api/me/sessions/{foreign.pk}/").status_code, 404
        )

    def test_last_seen_is_stamped_once_a_minute(self):
        self.make_user()
        self.login()
        old = timezone.now() - timedelta(hours=1)
        UserSession.objects.update(last_seen_at=old)
        self.client.get("/api/me/")  # login already stamped the session: no write
        self.assertEqual(UserSession.objects.get().last_seen_at, old)
        session = self.client.session
        session["last_seen"] = 0
        session.save()
        self.client.get("/api/me/")  # past the interval: stamped
        self.assertGreater(
            UserSession.objects.get().last_seen_at,
            timezone.now() - timedelta(minutes=1),
        )

    def test_clear_expired_sessions_task(self):
        user = self.make_user()
        UserSession.objects.create(
            user=user, session_key="dead" * 8, last_seen_at=timezone.now()
        )
        UserSession.objects.filter(session_key="dead" * 8).update(
            created_at=timezone.now() - timedelta(hours=1)
        )
        self.assertEqual(tasks.clear_expired_sessions(), 1)


class DeletionTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.user = self.make_user()
        self.login()

    def test_start_then_cancel(self):
        response = self.post("/api/me/delete/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.json()["data"]["deletion_scheduled_for"])
        # account endpoints stay open while pending; the gate itself is covered below
        self.assertEqual(self.client.get("/api/me/").status_code, 200)
        self.assertEqual(self.post("/api/me/delete/cancel/").status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_deleted)

    def test_login_during_grace_cancels_deletion(self):
        self.post("/api/auth/logout/")
        User.objects.filter(pk=self.user.pk).update(
            is_deleted=True, deleted_at=timezone.now()
        )
        self.assertEqual(self.login().status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_deleted)

    def test_blocked_while_owning_project(self):
        check = lambda user: True
        deletion_service.ownership_checks.append(check)
        self.addCleanup(deletion_service.ownership_checks.remove, check)
        response = self.post("/api/me/delete/")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "owns_projects")

    def test_purge_removes_only_expired(self):
        old = self.make_user("old@example.com")
        recent = self.make_user("recent@example.com")
        User.objects.filter(pk=old.pk).update(
            is_deleted=True, deleted_at=timezone.now() - timedelta(days=8)
        )
        User.objects.filter(pk=recent.pk).update(
            is_deleted=True, deleted_at=timezone.now() - timedelta(days=2)
        )
        self.assertEqual(tasks.purge_deleted_accounts(), 1)
        self.assertFalse(User.objects.filter(pk=old.pk).exists())
        self.assertTrue(User.objects.filter(pk=recent.pk).exists())


class PendingDeletionGateTests(TestCase):
    def test_permission_blocks_pending_deletion(self):
        from rest_framework.test import APIRequestFactory

        from accounts.permissions import IsProfileComplete
        from common.exception.domain import PermissionDeniedException

        user = User.objects.create_user(
            "d@example.com", None, first_name="D", last_name="D", display_name="D"
        )
        user.delete()
        request = APIRequestFactory().get("/")
        request.user = user
        with self.assertRaises(PermissionDeniedException):
            IsProfileComplete().has_permission(request, None)
