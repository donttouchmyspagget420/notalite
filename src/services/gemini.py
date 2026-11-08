import requests
from flask import current_app


class LlmError(Exception):
    pass


def generate_text(prompt):
    api_key = current_app.config.get("GOOGLE_LLM_API_KEY")

    if not api_key:
        raise LlmError(
            "Falta configurar GOOGLE_LLM_API_KEY para usar el asistente de IA."
        )

    model = current_app.config.get("GOOGLE_LLM_MODEL")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
    )

    try:
        response = requests.post(
            url,
            params={"key": api_key},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
    except requests.RequestException as error:
        raise LlmError("No se pudo conectar con Google Gemini.") from error

    if response.status_code >= 400:
        raise LlmError("Google Gemini rechazó la solicitud.")

    try:
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise LlmError("La respuesta de Google Gemini no contiene texto.") from error
