import io
from unittest import mock

from PIL import Image

from attachments.models import Attachment
from attachments.services import image_service
from attachments.tests.base import (
    JPEG,
    PDF,
    PNG,
    AttachmentTestCase,
    image_bytes,
    pdf_bytes,
)


class ImageProcessingTests(AttachmentTestCase):
    def test_exif_is_stripped_and_size_adjusted(self):
        data = image_bytes("JPEG", exif=True)
        self.assertIn(b"SecretCamera", data)
        attachment = self.attach(data, filename="p.jpg", content_type=JPEG)
        key = self.key_of(attachment)
        stored, content_type = self.storage.objects[key]
        self.assertEqual(content_type, JPEG)
        self.assertNotIn(b"SecretCamera", stored)
        with Image.open(io.BytesIO(stored)) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.size, (64, 48))
        row = Attachment.objects.get(pk=attachment["id"])
        self.assertEqual((row.status, row.size_bytes), ("ready", len(stored)))
        self.assertEqual(self.my_usage()["bytes_used"], len(stored))
        self.assertEqual(self.project_usage()["bytes_used"], len(stored))

    def test_png_and_webp_survive_reencoding(self):
        for fmt, mime in (("PNG", PNG), ("WEBP", "image/webp")):
            attachment = self.attach(image_bytes(fmt), filename="x", content_type=mime)
            stored, _ = self.storage.objects[self.key_of(attachment)]
            with Image.open(io.BytesIO(stored)) as image:
                self.assertEqual(image.format, fmt)

    def test_gif_is_left_alone(self):
        data = image_bytes("GIF")
        attachment = self.attach(data, filename="x.gif", content_type="image/gif")
        self.assertEqual(attachment["status"], "ready")
        self.assertEqual(self.storage.objects[self.key_of(attachment)][0], data)

    def test_corrupt_image_is_removed_and_quota_freed(self):
        # Valid PNG header and signature, garbage body: passes the sniff,
        # fails decoding.
        broken = image_bytes("PNG")[:40] + b"\x00" * 60
        attachment = self.attach(broken, filename="x.png", content_type=PNG)
        self.assertFalse(Attachment.objects.filter(pk=attachment["id"]).exists())
        self.assertNotIn(self.key_of_gone(attachment), self.storage.objects)
        self.assertEqual(self.my_usage()["bytes_used"], 0)

    def key_of_gone(self, attachment: dict) -> str:
        return f"projects/{self.pid}/attachments/{attachment['id']}"

    def test_decompression_bomb_guard(self):
        data = image_bytes("PNG", size=(40, 40))
        with mock.patch.object(image_service.limits, "MAX_IMAGE_PIXELS", 100):
            attachment = self.attach(data, filename="x.png", content_type=PNG)
        self.assertFalse(Attachment.objects.filter(pk=attachment["id"]).exists())

    def test_processing_images_cannot_be_downloaded_yet(self):
        data = image_bytes("PNG")
        with mock.patch("attachments.tasks.process_image.delay"):
            attachment = self.attach(data, filename="x.png", content_type=PNG)
        self.assertEqual(attachment["status"], "processing")
        denied = self.get(self.url(f"attachments/{attachment['id']}/download/"))
        self.assertEqual(denied.json()["code"], "attachment_not_ready")
        # It is already listed, so the UI can show a spinner.
        self.assertEqual(len(self.items("attachments/", task=self.task["number"])), 1)


class AccessTests(AttachmentTestCase):
    def test_member_uploads_and_deletes_own_but_not_others(self):
        owners = self.attach(pdf_bytes(), content_type=PDF, filename="o.pdf")
        self.switch("bob@example.com")
        mine = self.attach(pdf_bytes(), content_type=PDF, filename="b.pdf")
        denied = self.delete(self.url(f"attachments/{owners['id']}/"))
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(
            self.delete(self.url(f"attachments/{mine['id']}/")).status_code, 200
        )
        self.switch("owner@example.com")
        self.assertEqual(
            self.delete(self.url(f"attachments/{owners['id']}/")).status_code, 200
        )

    def test_owner_can_delete_a_members_file(self):
        self.switch("bob@example.com")
        mine = self.attach(pdf_bytes(), content_type=PDF, filename="b.pdf")
        self.switch("owner@example.com")
        self.assertEqual(
            self.delete(self.url(f"attachments/{mine['id']}/")).status_code, 200
        )

    def test_non_member_gets_404_everywhere(self):
        attachment = self.attach(pdf_bytes(), content_type=PDF, filename="a.pdf")
        self.make_user("eve@example.com")
        self.switch("eve@example.com")
        for response in (
            self.request_upload("a.pdf", PDF, 10),
            self.get(self.url("attachments/")),
            self.get(self.url(f"attachments/{attachment['id']}/download/")),
            self.delete(self.url(f"attachments/{attachment['id']}/")),
            self.get(self.url("storage/")),
        ):
            self.assertEqual(response.status_code, 404)

    def test_attachment_of_another_project_is_not_reachable(self):
        attachment = self.attach(pdf_bytes(), content_type=PDF, filename="a.pdf")
        other = self.create_project(name="Other", task_key="OTH")
        url = f"/api/projects/{other['id']}/attachments/{attachment['id']}/download/"
        self.assertEqual(self.get(url).status_code, 404)

    def test_archived_project_blocks_upload_not_download(self):
        attachment = self.attach(pdf_bytes(), content_type=PDF, filename="a.pdf")
        self.post(self.url("archive/"))
        blocked = self.request_upload("b.pdf", PDF, 10)
        self.assertEqual(blocked.json()["code"], "project_archived")
        self.assertEqual(
            self.get(self.url(f"attachments/{attachment['id']}/download/")).status_code,
            200,
        )
        self.assertEqual(
            self.delete(self.url(f"attachments/{attachment['id']}/")).status_code, 409
        )

    def test_upload_url_is_rate_limited(self):
        with mock.patch.dict(
            "rest_framework.throttling.ScopedRateThrottle.THROTTLE_RATES",
            {"attachment_upload": "2/hour"},
        ):
            codes = [
                self.request_upload("a.png", PNG, 10).status_code for _ in range(3)
            ]
        self.assertEqual(codes, [201, 201, 429])

    def test_unknown_body_fields_rejected(self):
        response = self.post(
            self.url("attachments/upload-url/"),
            {
                "target_type": "task",
                "target": "1",
                "filename": "a",
                "content_type": PDF,
                "size": 5,
                "object_key": "evil",
            },
        )
        self.assertEqual(response.status_code, 400)
