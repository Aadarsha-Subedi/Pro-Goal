from attachments.tests.base import AttachmentTestCase, image_bytes


class NoteImageTests(AttachmentTestCase):
    def note(self, body: str):
        return self.post(self.url("notes/"), {"title": "n", "body": body})

    def image_attachment(self) -> dict:
        return self.attach(
            image_bytes("PNG"), filename="a.png", content_type="image/png"
        )

    def test_project_attachment_images_are_allowed(self):
        image = self.image_attachment()
        response = self.note(f"text ![diagram](attachment:{image['id']}) more")
        self.assertEqual(response.status_code, 201)
        titled = self.note(f'![d](attachment:{image["id"]} "Title")')
        self.assertEqual(titled.status_code, 201)

    def test_external_and_raw_html_images_are_refused(self):
        for body in (
            "![x](https://evil.example/x.png)",
            "![x](http://evil.example/x.png)",
            "![x](//evil.example/x.png)",
            "![x](data:image/png;base64,AAAA)",
            '<img src="https://evil.example/x.png">',
            "<IMG src=x>",
            "![x][ref]\n\n[ref]: https://evil.example/x.png",
            "![x](/relative/path.png)",
        ):
            response = self.note(body)
            self.assertEqual(response.status_code, 400, body)
            self.assertEqual(response.json()["code"], "invalid_note_image", body)

    def test_other_projects_and_unknown_attachments_are_refused(self):
        other = self.create_project(name="Other", task_key="OTH")
        foreign_task = self.post(
            f"/api/projects/{other['id']}/tasks/", {"title": "t"}
        ).json()["data"]
        body = {
            "target_type": "task",
            "target": str(foreign_task["number"]),
            "filename": "a.png",
            "content_type": "image/png",
            "size": 10,
        }
        pending = self.post(
            f"/api/projects/{other['id']}/attachments/upload-url/", body
        )
        foreign_id = pending.json()["data"]["attachment"]["id"]
        self.assertEqual(self.note(f"![x](attachment:{foreign_id})").status_code, 400)
        missing = "00000000-0000-0000-0000-000000000000"
        self.assertEqual(self.note(f"![x](attachment:{missing})").status_code, 400)

    def test_pending_attachment_cannot_be_embedded(self):
        pending = self.upload(
            image_bytes("PNG"), filename="a.png", content_type="image/png"
        )
        self.assertEqual(
            self.note(f"![x](attachment:{pending['id']})").status_code, 400
        )

    def test_update_is_validated_too_and_links_are_not_images(self):
        note = self.note("plain").json()["data"]
        bad = self.patch(
            self.url(f"notes/{note['id']}/"),
            {"version": 1, "body": "![x](https://evil.example/x.png)"},
        )
        self.assertEqual(bad.json()["code"], "invalid_note_image")
        ok = self.patch(
            self.url(f"notes/{note['id']}/"),
            {"version": 1, "body": "[a link](https://example.com) is fine"},
        )
        self.assertEqual(ok.status_code, 200)
