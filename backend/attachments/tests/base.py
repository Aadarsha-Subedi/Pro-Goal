import io
import zipfile
from unittest import mock

from PIL import Image

from attachments.models import Attachment
from common.storage.memory import InMemoryStorage
from tracker.tests.base import TrackerTestCase

PNG = "image/png"
JPEG = "image/jpeg"
PDF = "application/pdf"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def image_bytes(
    fmt: str = "PNG", size: tuple[int, int] = (64, 48), exif: bool = False
) -> bytes:
    out = io.BytesIO()
    image = Image.new("RGB", size, "red")
    kwargs = {}
    if exif:
        exif_data = Image.Exif()
        exif_data[0x010F] = "SecretCamera"  # Make
        kwargs["exif"] = exif_data
    image.save(out, format=fmt, **kwargs)
    return out.getvalue()


def pdf_bytes(size: int = 200) -> bytes:
    return b"%PDF-1.4\n" + b"x" * (size - 9)


def docx_bytes() -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("_rels/.rels", "<r/>")
        archive.writestr("word/document.xml", "<x/>")
    return out.getvalue()


class AttachmentTestCase(TrackerTestCase):
    """Uses the in-memory storage in place of R2."""

    def setUp(self) -> None:
        super().setUp()
        self.storage = InMemoryStorage()
        for target in ("attachments.services.storage.get_storage",):
            patcher = mock.patch(target, return_value=self.storage)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.task = self.create_task("With files")

    # Flow helpers
    def request_upload(
        self, filename="photo.png", content_type=PNG, size=100, **target
    ):
        body = {
            "target_type": "task",
            "target": str(self.task["number"]),
            "filename": filename,
            "content_type": content_type,
            "size": size,
            **target,
        }
        return self.post(self.url("attachments/upload-url/"), body)

    def upload(
        self, data: bytes, filename="photo.png", content_type=PNG, **target
    ) -> dict:
        """upload-url, the browser's PUT, and confirm. Returns the attachment."""
        response = self.request_upload(filename, content_type, len(data), **target)
        assert response.status_code == 201, response.content
        attachment = response.json()["data"]["attachment"]
        key = Attachment.objects.get(pk=attachment["id"]).object_key
        self.storage.simulate_browser_put(key, data)
        return attachment

    def confirm(self, attachment_id: str):
        return self.post(self.url(f"attachments/{attachment_id}/confirm/"))

    def attach(self, data: bytes, **kwargs) -> dict:
        attachment = self.upload(data, **kwargs)
        response = self.confirm(attachment["id"])
        assert response.status_code == 200, response.content
        return response.json()["data"]

    def key_of(self, attachment: dict) -> str:
        return Attachment.objects.get(pk=attachment["id"]).object_key

    def project_usage(self) -> dict:
        return self.get(self.url("storage/")).json()["data"]

    def my_usage(self) -> dict:
        return self.get("/api/me/storage/").json()["data"]
