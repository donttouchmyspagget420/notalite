import unittest
from unittest.mock import Mock, patch

from config import Config
from src import create_app
from src.llm.gemini import LlmError, generate_text


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

    def test_generate_text_reads_candidate(self):
        app = make_app()
        response = Mock(status_code=200)
        response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "  respuesta  "}]}}]
        }

        with app.app_context(), patch(
            "src.llm.gemini.requests.post", return_value=response
        ) as post:
            result = generate_text("hola")

        self.assertEqual(result, "respuesta")
        _, kwargs = post.call_args
        self.assertEqual(kwargs["params"], {"key": "test-key"})
        self.assertIn("gemini-test:generateContent", post.call_args.args[0])

    def test_http_error_raises(self):
        app = make_app()
        response = Mock(status_code=429)

        with app.app_context(), patch(
            "src.llm.gemini.requests.post", return_value=response
        ):
            with self.assertRaises(LlmError) as context:
                generate_text("hola")

        self.assertIn("rechazó", str(context.exception))
