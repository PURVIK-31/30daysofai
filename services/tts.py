import requests


def generate_tts_murf(text: str, api_key: str, voice_id: str) -> str:
    """Generate TTS audio via Murf REST API and return the audio file URL.

    Raises requests.RequestException on HTTP errors for callers to handle.
    """
    endpoint = "https://api.murf.ai/v1/speech/generate"
    payload = {"text": text, "voiceId": voice_id}
    headers = {"api-key": api_key, "Content-Type": "application/json"}

    response = requests.post(endpoint, json=payload, headers=headers, timeout=60)
    response.raise_for_status()
    data = response.json()
    return data.get("audioFile", "")



