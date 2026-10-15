from django.core import mail
from django.test import SimpleTestCase, override_settings

from common.email.render import LOGO_CID, build_message


@override_settings(FRONTEND_URL="https://app.example.com")
class EmailRenderTests(SimpleTestCase):
    def html(self, message) -> str:
        return message.alternatives[0].content

    def test_first_link_becomes_a_button_and_leaves_the_text(self):
        message = build_message(
            "Verify your email",
            "Confirm your email within 24 hours:\n\n"
            "https://app.example.com/verify-email?token=abc\n",
            "ada@example.com",
        )
        html = self.html(message)
        self.assertIn('href="https://app.example.com/verify-email?token=abc"', html)
        self.assertIn("Verify email", html)  # label chosen from the link
        self.assertIn("Confirm your email within 24 hours.", html)
        self.assertEqual(
            html.count("verify-email?token=abc"), 3
        )  # button, box and its link
        self.assertEqual(message.body.count("verify-email?token=abc"), 1)

    def test_text_part_is_kept_and_logo_is_inline(self):
        message = build_message("Hi", "Hello.\n", "ada@example.com")
        self.assertEqual(message.body, "Hello.\n")
        self.assertIn(f"cid:{LOGO_CID}", self.html(message))
        self.assertEqual(message.attachments[0]["Content-ID"], f"<{LOGO_CID}>")
        message.message()  # the whole thing must serialise

    def test_no_link_means_no_button(self):
        html = self.html(build_message("Removed", "You were removed.\n", "a@b.co"))
        self.assertNotIn("Button not working", html)

    def test_explicit_label_wins(self):
        html = self.html(
            build_message("x", "Go https://app.example.com/login\n", "a@b.co", "Do it")
        )
        self.assertIn("Do it", html)

    def test_text_is_escaped(self):
        html = self.html(
            build_message("<b>x</b>", "<script>alert(1)</script>\n", "a@b.co")
        )
        self.assertNotIn("<script>", html)
        self.assertNotIn("<b>x</b>", html)

    def test_sent_through_the_outbox(self):
        build_message("Hi", "Hello.\n", "ada@example.com").send()
        self.assertEqual(mail.outbox[0].to, ["ada@example.com"])
