from unittest.mock import patch

from src.extensions import db
from src.models import Note
from src.services.gemini import LlmError
from src.tests.base import BaseTestCase


class AiAssistTestCase(BaseTestCase):
    def test_editor_has_ai_controls(self):
        html = self.client.get(f"/notes/{self.note.id}").get_data(as_text=True)

        self.assertIn('id="aiModal"', html)
        self.assertIn('data-ai-action="summarize"', html)
        self.assertIn('data-ai-action="custom"', html)

    @patch("src.notes.routes.generate_text", return_value="Resumen generado")
    def test_summarize_note(self, generate_text):
        response = self.client.post(
            f"/notes/{self.note.id}/ai",
            json={"action": "summarize"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"ok": True, "text": "Resumen generado"})
        prompt = generate_text.call_args.args[0]
        self.assertIn("Resumí", prompt)
        self.assertIn("Hello world", prompt)

    @patch("src.notes.routes.generate_text", return_value="Texto mejorado")
    def test_uses_selected_text(self, generate_text):
        response = self.client.post(
            f"/notes/{self.note.id}/ai",
            json={"action": "improve", "selection": "Texto elegido"},
        )

        self.assertEqual(response.status_code, 200)
        prompt = generate_text.call_args.args[0]
        self.assertIn("Texto elegido", prompt)
        self.assertNotIn("Hello world", prompt)

    @patch("src.notes.routes.generate_text", return_value="Resultado")
    def test_accepts_form_payload(self, _generate_text):
        response = self.client.post(
            f"/notes/{self.note.id}/ai",
            data={"action": "summarize"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["text"], "Resultado")

    @patch("src.notes.routes.generate_text", return_value="Resultado")
    def test_custom_instruction(self, generate_text):
        response = self.client.post(
            f"/notes/{self.note.id}/ai",
            json={"action": "custom", "prompt": "Convertí esto en pasos"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Convertí esto en pasos", generate_text.call_args.args[0])

    def test_custom_instruction_is_required(self):
        response = self.client.post(
            f"/notes/{self.note.id}/ai",
            json={"action": "custom", "prompt": "   "},
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["ok"])

    def test_empty_note_is_rejected(self):
        self.note.content = ""
        db.session.commit()

        response = self.client.post(
            f"/notes/{self.note.id}/ai",
            json={"action": "summarize"},
        )

        self.assertEqual(response.status_code, 400)

    @patch(
        "src.notes.routes.generate_text",
        side_effect=LlmError("Falta configurar GOOGLE_LLM_API_KEY."),
    )
    def test_llm_errors_are_reported(self, _generate_text):
        response = self.client.post(
            f"/notes/{self.note.id}/ai",
            json={"action": "summarize"},
        )

        self.assertEqual(response.status_code, 502)
        payload = response.get_json()
        self.assertFalse(payload["ok"])
        self.assertIn("GOOGLE_LLM_API_KEY", payload["error"])

    def test_cannot_use_ai_on_another_users_note(self):
        other = self.create_user()
        other_note = Note(
            title="Private",
            name="private.md",
            content="secret",
            user_id=other.id,
        )
        db.session.add(other_note)
        db.session.commit()

        response = self.client.post(
            f"/notes/{other_note.id}/ai",
            json={"action": "summarize"},
        )

        self.assertEqual(response.status_code, 404)

    def test_ai_requires_login(self):
        response = self.app.test_client().post(
            f"/notes/{self.note.id}/ai",
            json={"action": "summarize"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.headers["Location"])
