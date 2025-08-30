from typing import List, Optional, Dict
from pydantic import BaseModel


class TTSRequest(BaseModel):
    text: str


class TTSGenerateResponse(BaseModel):
    success: bool
    audio_url: Optional[str] = None
    message: Optional[str] = None
    raw_response: Optional[Dict] = None
    fallback_text: Optional[str] = None


class UploadAudioResponse(BaseModel):
    filename: str
    content_type: str
    size: int


class TranscriptionResponse(BaseModel):
    transcript: str


class TTSEchoResponse(BaseModel):
    success: bool
    audio_url: Optional[str] = None
    transcript: Optional[str] = None
    message: Optional[str] = None
    raw_response: Optional[Dict] = None
    fallback_text: Optional[str] = None


class LLMQueryRequest(BaseModel):
    text: str
    model: Optional[str] = None


class LLMQueryTextResponse(BaseModel):
    success: bool
    model: str
    response: Optional[str] = None
    message: Optional[str] = None
    raw_response: Optional[Dict] = None
    fallback_text: Optional[str] = None


class LLMVoicePipelineResponse(BaseModel):
    success: bool
    model: str
    audio_url: Optional[str] = None
    transcript: Optional[str] = None
    llm_text: Optional[str] = None
    truncated_for_tts: Optional[bool] = None
    message: Optional[str] = None
    raw_response: Optional[Dict] = None
    fallback_text: Optional[str] = None


class AgentChatResponse(BaseModel):
    success: bool
    model: str
    audio_url: Optional[str] = None
    transcript: Optional[str] = None
    llm_text: Optional[str] = None
    truncated_for_tts: Optional[bool] = None
    history_len: Optional[int] = None
    message: Optional[str] = None
    raw_response: Optional[Dict] = None
    fallback_text: Optional[str] = None


class ChatMessage(BaseModel):
    role: str
    text: str


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: List[ChatMessage]
    count: int



