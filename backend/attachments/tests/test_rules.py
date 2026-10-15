from attachments.models import Attachment
from attachments.tests.base import (
    DOCX,
    JPEG,
    PDF,
    PNG,
    AttachmentTestCase,
    docx_bytes,
    image_bytes,
    pdf_bytes,
)

MB = 1024 * 1024


class TypeRuleTests(AttachmentTestCase):
    def refuse_at_request(self, content_type: str, size: int = 100):
        response = self.request_upload("f", content_type, size)
        self.assertEqual(response.status_code, 400, content_type)
        return response.json()["code"]

    def test_disallowed_declared_types(self):
        for content_type in (
            "image/svg+xml",
            "text/html",
            "application/x-msdownload",
            "application/zip",
            "video/mp4",
            "video/webm",
            "application/msword",
            "application/vnd.ms-excel",
            "application/octet-stream",
        ):
            self.assertEqual(
                self.refuse_at_request(content_type), "file_type_not_allowed"
            )

    def test_size_limits_per_category(self):
        self.assertEqual(self.refuse_at_request(PNG, 5 * MB + 1), "file_too_large")
        self.assertEqual(self.refuse_at_request(PDF, 10 * MB + 1), "file_too_large")
        self.assertEqual(
            self.refuse_at_request("audio/mpeg", 20 * MB + 1), "file_too_large"
        )
        self.assertEqual(self.request_upload("ok.png", PNG, 5 * MB).status_code, 201)
        self.assertEqual(self.request_upload("ok.pdf", PDF, 10 * MB).status_code, 201)
        self.assertEqual(
            self.request_upload("ok.mp3", "audio/mpeg", 20 * MB).status_code, 201
        )

    def test_zero_size_rejected(self):
        self.assertEqual(self.request_upload("e.pdf", PDF, 0).status_code, 400)

    def assert_discarded(self, attachment: dict, code: str):
        response = self.confirm(attachment["id"])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], code)
        self.assertFalse(Attachment.objects.filter(pk=attachment["id"]).exists())
        self.assertNotIn(self.key_of_gone(attachment), self.storage.objects)

    def key_of_gone(self, attachment: dict) -> str:
        return f"projects/{self.pid}/attachments/{attachment['id']}"

    def test_extension_spoofing_is_caught_by_content(self):
        # An executable uploaded as "photo.png" / image/png.
        attachment = self.upload(
            b"MZ" + b"\x00" * 200, filename="photo.png", content_type=PNG
        )
        self.assert_discarded(attachment, "file_type_not_allowed")

    def test_declared_type_must_match_real_type(self):
        attachment = self.upload(
            image_bytes("PNG"), filename="a.jpg", content_type=JPEG
        )
        self.assert_discarded(attachment, "file_type_not_allowed")

    def test_svg_disguised_as_text_or_image_is_refused(self):
        svg = b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>"
        as_image = self.upload(svg, filename="x.png", content_type=PNG)
        self.assert_discarded(as_image, "file_type_not_allowed")

    def test_plain_text_must_be_text(self):
        good = self.attach(
            b"hello \xc3\xa9 world\n", filename="n.txt", content_type="text/plain"
        )
        self.assertEqual(good["content_type"], "text/plain")
        binary = self.upload(b"abc\x00def", filename="n.txt", content_type="text/plain")
        self.assert_discarded(binary, "file_type_not_allowed")
        exe = self.upload(
            b"MZ\x90\x00" + b"\x01" * 50, filename="n.txt", content_type="text/plain"
        )
        self.assert_discarded(exe, "file_type_not_allowed")

    def test_size_mismatch_at_confirm(self):
        response = self.request_upload("a.pdf", PDF, 300)
        attachment = response.json()["data"]["attachment"]
        self.storage.simulate_browser_put(self.key_of(attachment), pdf_bytes(250))
        self.assert_discarded(attachment, "upload_size_mismatch")

    def test_sniffed_category_limit_is_rechecked(self):
        # Declared as a PDF (10 MB limit) but really an audio file would pass
        # the PDF check only if the types matched: they do not, so it is refused.
        attachment = self.upload(
            b"ID3\x03\x00\x00\x00\x00\x00\x00" + b"\x00" * 50,
            filename="a.pdf",
            content_type=PDF,
        )
        self.assert_discarded(attachment, "file_type_not_allowed")

    def test_accepts_each_allowed_family(self):
        cases = [
            (image_bytes("PNG"), PNG),
            (image_bytes("JPEG"), JPEG),
            (image_bytes("WEBP"), "image/webp"),
            (image_bytes("GIF"), "image/gif"),
            (pdf_bytes(), PDF),
            (docx_bytes(), DOCX),
            (b"ID3\x03\x00\x00\x00\x00\x00\x00" + b"\x00" * 50, "audio/mpeg"),
            (
                b"\x00\x00\x00\x20ftypM4A \x00\x00\x00\x00M4A mp42isom" + b"\x00" * 40,
                "audio/mp4",
            ),
        ]
        for data, content_type in cases:
            attachment = self.attach(data, filename="f", content_type=content_type)
            self.assertIn(attachment["status"], ("ready", "processing"), content_type)
