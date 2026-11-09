from flask import current_app
from google import genai


class LlmError(Exception):
    pass


def generate_text(prompt):
    api_key = current_app.config.get("GOOGLE_LLM_API_KEY")

    if not api_key:
        raise LlmError(
            "Falta configurar GOOGLE_LLM_API_KEY para usar el asistente de IA."
        )

    client = genai.Client(api_key=api_key)
    model = current_app.config.get("GOOGLE_LLM_MODEL")

    try:
        output = client.interactions.create(
            model=model,
            input=prompt,
        )

        return output.output_text.strip()
    except Exception as error:
        raise LlmError("No se pudo conectar con Google Gemini.") from error
