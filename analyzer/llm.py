"""Tiny client for the local Ollama server. Both LLM jobs (categorize, summarize) go through here."""

import requests

from analyzer.config import LLM_TIMEOUT, MODEL_NAME, OLLAMA_URL


def is_available() -> bool:
    """True if Ollama answers and the configured model is pulled."""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        response.raise_for_status()
    except requests.RequestException:
        return False
    names = [m.get("name", "") for m in response.json().get("models", [])]
    wanted = MODEL_NAME if ":" in MODEL_NAME else f"{MODEL_NAME}:latest"
    return wanted in names


def chat(
    system: str,
    user: str,
    json_mode: bool = False,
    temperature: float = 0.0,
    max_tokens: int | None = None,
) -> str:
    """Send one system + user message and return the model's raw text reply.

    Raises requests.RequestException if the server is down or slow; callers decide the fallback.
    """
    options: dict = {"temperature": temperature}
    if max_tokens:
        options["num_predict"] = max_tokens
    payload = {
        "model": MODEL_NAME,
        "stream": False,
        "options": options,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    if json_mode:
        payload["format"] = "json"
    response = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=LLM_TIMEOUT)
    response.raise_for_status()
    return response.json()["message"]["content"]
