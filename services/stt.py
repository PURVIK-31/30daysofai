import assemblyai as aai


def transcribe_audio_bytes(audio_bytes: bytes, api_key: str) -> str:
    """Transcribe raw audio bytes using AssemblyAI SDK and return the text.

    Attempts to use SDK upload helper when available, otherwise falls back to
    passing raw bytes directly to the transcriber.
    """
    aai.settings.api_key = api_key
    transcriber = aai.Transcriber()

    try:
        upload_url = transcriber.upload_file(audio_bytes)  # type: ignore[attr-defined]
        transcript = transcriber.transcribe(upload_url)
    except AttributeError:
        transcript = transcriber.transcribe(audio_bytes)

    return (transcript.text or "").strip()



