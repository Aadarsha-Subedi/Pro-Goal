from attachments.models import Attachment
from attachments.tests.base import (
    DOCX,
    PDF,
    PNG,
    AttachmentTestCase,
    docx_bytes,
    image_bytes,
    pdf_bytes,
)


class UploadFlowTests(AttachmentTestCase):
    def test_full_flow_for_a_pdf(self):
        data = pdf_bytes(300)
        response = self.request_upload("Spec.pdf", PDF, len(data))
        self.assertEqual(response.status_code, 201)
        upload = response.json()["data"]["upload"]
        self.assertEqual(upload["method"], "PUT")
        self.assertIn("/put/projects/", upload["url"])
        self.assertEqual(upload["headers"], {"Content-Type": PDF})
        attachment = response.json()["data"]["attachment"]
        self.assertEqual(attachment["status"], "pending")
        key = self.key_of(attachment)
        self.assertTrue(key.startswith(f"projects/{self.pid}/attachments/"))
        self.assertEqual(self.storage.presigned_puts[key], (PDF, 300))

        self.storage.simulate_browser_put(key, data)
        confirmed = self.confirm(attachment["id"]).json()["data"]
        self.assertEqual(
            (confirmed["status"], confirmed["category"]), ("ready", "document")
        )

        listing = self.items("attachments/", task=self.task["number"])
        self.assertEqual([a["filename"] for a in listing], ["Spec.pdf"])

        download = self.get(self.url(f"attachments/{attachment['id']}/download/"))
        self.assertIn("disposition=attachment", download.json()["data"]["url"])
        self.assertIn("filename=Spec.pdf", download.json()["data"]["url"])

    def test_docx_is_recognised(self):
        data = docx_bytes()
        attachment = self.attach(data, filename="notes.docx", content_type=DOCX)
        self.assertEqual(attachment["content_type"], DOCX)

    def test_images_are_served_inline_after_processing(self):
        data = image_bytes("PNG")
        confirmed = self.attach(data)
        # Eager Celery re-encodes the image before the response is built.
        self.assertEqual(
            self.items("attachments/", task=self.task["number"])[0]["status"], "ready"
        )
        url = self.get(self.url(f"attachments/{confirmed['id']}/download/")).json()[
            "data"
        ]["url"]
        self.assertIn("disposition=inline", url)

    def test_confirm_twice_is_harmless_and_only_uploader_confirms(self):
        attachment = self.upload(pdf_bytes(), content_type=PDF, filename="a.pdf")
        self.confirm(attachment["id"])
        self.assertEqual(self.confirm(attachment["id"]).status_code, 200)
        self.switch("bob@example.com")
        self.assertEqual(self.confirm(attachment["id"]).status_code, 404)

    def test_confirm_without_upload(self):
        response = self.request_upload("a.pdf", PDF, 100)
        attachment = response.json()["data"]["attachment"]
        missing = self.confirm(attachment["id"])
        self.assertEqual(missing.json()["code"], "upload_missing")
        self.assertTrue(Attachment.objects.filter(pk=attachment["id"]).exists())

    def test_download_needs_ready_and_membership(self):
        pending = self.upload(pdf_bytes(), content_type=PDF, filename="a.pdf")
        url = self.url(f"attachments/{pending['id']}/download/")
        self.assertEqual(self.get(url).json()["code"], "attachment_not_ready")
        self.confirm(pending["id"])
        self.assertEqual(self.get(url).status_code, 200)
        self.make_user("eve@example.com")
        self.switch("eve@example.com")
        self.assertEqual(self.get(url).status_code, 404)

    def test_list_hides_pending_and_filters_by_target(self):
        note = self.post(self.url("notes/"), {"title": "n"}).json()["data"]
        self.attach(pdf_bytes(), filename="on-task.pdf", content_type=PDF)
        self.upload(pdf_bytes(), filename="pending.pdf", content_type=PDF)
        on_note = self.attach(
            pdf_bytes(),
            filename="on-note.pdf",
            content_type=PDF,
            target_type="note",
            target=note["id"],
        )
        self.assertEqual(
            [
                a["filename"]
                for a in self.items("attachments/", task=self.task["number"])
            ],
            ["on-task.pdf"],
        )
        self.assertEqual(
            [a["id"] for a in self.items("attachments/", note=note["id"])],
            [on_note["id"]],
        )
        self.assertEqual(len(self.items("attachments/")), 2)

    def test_comment_target(self):
        comment = self.post(
            self.url(f"tasks/{self.task['number']}/comments/"), {"body": "hi"}
        ).json()["data"]
        attached = self.attach(
            pdf_bytes(),
            content_type=PDF,
            filename="c.pdf",
            target_type="comment",
            target=comment["id"],
        )
        self.assertEqual(attached["target"], {"type": "comment", "id": comment["id"]})

    def test_unknown_or_foreign_target(self):
        missing = self.request_upload(target="999")
        self.assertEqual(missing.status_code, 404)
        other = self.create_project(name="Other", task_key="OTH")
        foreign = self.post(
            f"/api/projects/{other['id']}/notes/", {"title": "x"}
        ).json()["data"]
        response = self.request_upload(target_type="note", target=foreign["id"])
        self.assertEqual(response.json()["code"], "attachment_target_not_found")

    def test_filename_is_sanitised(self):
        response = self.request_upload("../..\\evil\x07.png")
        name = response.json()["data"]["attachment"]["filename"]
        self.assertNotIn("/", name)
        self.assertNotIn("\x07", name)
        self.assertNotIn("\\", name)

    def test_per_target_cap(self):
        for index in range(20):
            self.assertEqual(
                self.request_upload(f"{index}.png", PNG, 10).status_code, 201
            )
        full = self.request_upload("21.png", PNG, 10)
        self.assertEqual(full.json()["code"], "attachment_target_full")

    def test_local_storage_is_not_configured(self):
        from unittest import mock

        from common.storage.local import LocalFileStorage

        with mock.patch(
            "attachments.services.storage.get_storage", return_value=LocalFileStorage()
        ):
            response = self.request_upload("a.pdf", PDF, 100)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "attachments_not_configured")
        self.assertEqual(Attachment.objects.count(), 0)
        self.assertEqual(self.my_usage()["bytes_used"], 0)
