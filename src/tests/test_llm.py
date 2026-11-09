import unittest
from unittest.mock import Mock, patch

from config import Config
from src import create_app
from src.services.gemini import LlmError, generate_text


def make_app(**overrides):
    class TestConfig(Config):
        TESTING = True
        SECRET_KEY = "test-secret"
        WTF_CSRF_ENABLED = False
        SQLALCHEMY_DATABASE_URI = "sqlite://"
        GOOGLE_LLM_API_KEY = "test-key"
        GOOGLE_LLM_MODEL = "gemini-test"

    for key, value in overrides.items():
        setattr(TestConfig, key, value)

    return create_app(TestConfig)


class GeminiServiceTestCase(unittest.TestCase):
    def test_missing_key_raises(self):
        app = make_app(GOOGLE_LLM_API_KEY=None)

        with app.app_context():
            with self.assertRaises(LlmError) as context:
                generate_text("hola")

        self.assertIn("GOOGLE_LLM_API_KEY", str(context.exception))

    def test_generate_text_returns_output(self):
        app = make_app()
        client = Mock()
        client.interactions.create.return_value = Mock(output_text="  respuesta  ")

        with app.app_context(), patch(
            "src.services.gemini.genai.Client", return_value=client
        ) as client_class:
            result = generate_text("hola")

        self.assertEqual(result, "respuesta")
        client_class.assert_called_once_with(api_key="test-key")
        client.interactions.create.assert_called_once_with(
            model="gemini-test",
            input="hola",
        )

    def test_sdk_error_raises(self):
        app = make_app()
        client = Mock()
        client.interactions.create.side_effect = RuntimeError("boom")

        with app.app_context(), patch(
            "src.services.gemini.genai.Client", return_value=client
        ):
            with self.assertRaises(LlmError) as context:
                generate_text("hola")

        self.assertIn("No se pudo conectar", str(context.exception))
