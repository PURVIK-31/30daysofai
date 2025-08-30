import requests


def generate_text_gemini(prompt_text: str, api_key: str, model: str) -> str:
    """Call Gemini generateContent and return generated text (first candidate).

    Raises requests.RequestException on HTTP errors for callers to handle.
    """
    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    )
    payload = {"contents": [{"parts": [{"text": prompt_text}]}]}
    response = requests.post(
        endpoint, json=payload, headers={"Content-Type": "application/json"}, timeout=60
    )
    response.raise_for_status()
    data = response.json()

    candidates = data.get("candidates", [])
    if candidates:
        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        if parts and isinstance(parts[0], dict):
            return parts[0].get("text", "")
    return ""


def generate_text_gemini_with_contents(contents: list, api_key: str, model: str) -> str:
    """Call Gemini generateContent with role-based contents and return text.

    'contents' should be a list of dicts like: {"role": "user"|"model", "parts": [{"text": "..."}]}
    """
    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    )
    payload = {"contents": contents}
    response = requests.post(
        endpoint, json=payload, headers={"Content-Type": "application/json"}, timeout=60
    )
    response.raise_for_status()
    data = response.json()

    candidates = data.get("candidates", [])
    if candidates:
        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        if parts and isinstance(parts[0], dict):
            return parts[0].get("text", "")
    return ""


