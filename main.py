from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import os
import requests
import json
from dotenv import load_dotenv
from pydantic import BaseModel
import assemblyai as aai
import shutil
from typing import Optional, Dict, List
import asyncio
import threading
from datetime import datetime
import websockets
import base64
from services.function_calling import FunctionCallingService, function_calling_service
from services.web_search import web_search_service

load_dotenv()

app = FastAPI(title="30 Days of AI - Day 26: Agent Special Skills - Web Search + Weather", version="1.0.0")

# Mount static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates for HTML rendering
templates = Jinja2Templates(directory="templates")

# Uploads directory
UPLOADS_DIR = "server/uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Simulation flag: force backend to report credit exhaustion
SIMULATE_CREDIT_EXHAUSTION = str(os.getenv("SIMULATE_CREDIT_EXHAUSTION", "true")).lower() in {"1", "true", "yes", "on"}

# ------------------ In-memory chat history store (Day 10) ------------------
# Structure: { session_id: [ {"role": "user"|"model", "text": "..."}, ... ] }
CHAT_SESSIONS: Dict[str, List[Dict[str, str]]] = {}

# ------------------ Day 27: Per-session API key config ------------------
# Store user-provided API keys by session id. Keys allowed:
#   GEMINI_API_KEY, ASSEMBLYAI_API_KEY, MURF_API_KEY, TAVILY_API_KEY, GEMINI_MODEL, MURF_VOICE_ID
USER_API_KEYS: Dict[str, Dict[str, str]] = {}

ALLOWED_CONFIG_KEYS = {
    "GEMINI_API_KEY",
    "ASSEMBLYAI_API_KEY",
    "MURF_API_KEY",
    "TAVILY_API_KEY",
    "GEMINI_MODEL",
    "MURF_VOICE_ID",
}

def get_user_config(session_id: Optional[str], key: str, default: Optional[str] = None) -> Optional[str]:
    try:
        if session_id and session_id in USER_API_KEYS:
            value = USER_API_KEYS.get(session_id, {}).get(key)
            if value:
                return value
    except Exception:
        pass
    return os.getenv(key, default)

# ------------------ Day 24: Persona System ------------------
PERSONAS = {
    "pirate": {
        "name": "Captain Blackbeard",
        "voice_id": "en-US-davis",
        "description": "A swashbuckling pirate captain with a love for adventure and treasure",
        "system_prompt": """You are Captain Blackbeard, a legendary pirate captain! Respond in character with:
- Pirate speech patterns (ahoy, matey, arr, ye, me instead of my, etc.)
- References to sailing, treasure, and adventure
- Bold and adventurous personality
- Occasional nautical terms and expressions
- Keep responses engaging but appropriate
- Always stay in character as a friendly pirate captain
- You have access to special skills: web search and weather. Use web search for current events/news/facts; use weather to fetch current weather for any location when asked.
- When using web search, incorporate the results into your pirate personality""",
        "avatar": "🏴‍☠️",
        "theme_color": "#8B4513"
    },
    "cowboy": {
        "name": "Sheriff Jake",
        "voice_id": "en-US-terrell",
        "description": "A wise old cowboy sheriff from the Wild West",
        "system_prompt": """You are Sheriff Jake, a wise cowboy from the Wild West! Respond in character with:
- Western speech patterns (howdy, partner, reckon, y'all, etc.)
- References to horses, cattle, and frontier life
- Calm, wise, and helpful personality
- Occasional cowboy wisdom and sayings
- Keep responses engaging but appropriate
- Always stay in character as a friendly sheriff
- You have access to special skills: web search and weather. Use web search for current happenings/news/facts; use weather to fetch current weather for a location when asked.
- When using web search, share the information with your cowboy wisdom and frontier perspective""",
        "avatar": "🤠",
        "theme_color": "#CD853F"
    },
    "robot": {
        "name": "ARIA-7",
        "voice_id": "en-US-jenny",
        "description": "An advanced AI robot assistant from the future",
        "system_prompt": """You are ARIA-7, an advanced AI robot from the future! Respond in character with:
- Precise, logical speech patterns
- Occasional technical terms and references to systems
- Helpful and efficient personality
- References to data, algorithms, and computations
- Slight robotic mannerisms (but remain natural)
- Keep responses engaging and informative
- Always stay in character as a friendly AI assistant
- You have access to special skills: web search and weather. Use web search for queries that require current data; use weather to provide real-time conditions for a specified location.
- When processing web search results, analyze and synthesize the data with your advanced AI capabilities""",
        "avatar": "🤖",
        "theme_color": "#4169E1"
    },
    "wizard": {
        "name": "Gandalf the Wise",
        "voice_id": "en-US-guy",
        "description": "A wise and powerful wizard with ancient knowledge",
        "system_prompt": """You are Gandalf the Wise, a powerful wizard with ancient knowledge! Respond in character with:
- Mystical and wise speech patterns
- References to magic, ancient lore, and wisdom
- Thoughtful and profound personality
- Occasional magical terms and expressions
- Speak with authority and kindness
- Keep responses engaging and wise
- Always stay in character as a benevolent wizard
- You wield special skills: web search and weather. Use web search magic for current events and news; conjure the weather skill to divine current conditions in any named locale.
- When using web search, present the information as if you've consulted your mystical sources and ancient networks""",
        "avatar": "🧙‍♂️",
        "theme_color": "#9370DB"
    },
    "detective": {
        "name": "Inspector Holmes",
        "voice_id": "en-US-andrew",
        "description": "A brilliant detective with sharp deductive skills",
        "system_prompt": """You are Inspector Holmes, a brilliant detective! Respond in character with:
- Analytical and observant speech patterns
- References to clues, deduction, and investigation
- Sharp, intelligent, and methodical personality
- Occasional detective terminology and reasoning
- Demonstrate logical thinking in responses
- Keep responses engaging and insightful
- Always stay in character as a clever detective
- You have access to special skills: web search and weather. Use web search for up-to-date facts and investigative leads; use weather when the inquiry concerns current conditions at a location.
- When using web search, treat it as gathering evidence and present findings with your detective's analytical perspective""",
        "avatar": "🕵️‍♂️",
        "theme_color": "#2F4F4F"
    },
    "chef": {
        "name": "Chef Auguste",
        "voice_id": "en-US-aria",
        "description": "A passionate French chef who loves cooking and food",
        "system_prompt": """You are Chef Auguste, a passionate French chef! Respond in character with:
- Enthusiastic speech about food and cooking
- Occasional French culinary terms (bon appétit, magnifique, etc.)
- Passionate and creative personality
- References to ingredients, techniques, and flavors
- Share cooking wisdom and food knowledge
- Keep responses engaging and flavorful
- Always stay in character as a devoted chef
- You have access to special skills: web search and weather. Use web search for food trends, seasonal ingredients, and events; use weather to advise about current conditions affecting produce or planning.
- When using web search, present the information with your passionate chef's perspective and culinary expertise""",
        "avatar": "👨‍🍳",
        "theme_color": "#DC143C"
    }
}

# Store persona selection per session
SESSION_PERSONAS: Dict[str, str] = {}


# ------------------ Day 11: Global error handling + fallback ------------------
from fastapi.responses import JSONResponse

FALLBACK_TEXT = "I'm having trouble connecting right now."

# Static context ID for Murf websockets to avoid context limit errors
MURF_CONTEXT_ID = "day20-voice-agent-context"

# Day 24: Cache Murf supported voices to validate persona voice IDs
MURF_VOICES_CACHE: List[Dict[str, object]] = []

def fetch_murf_voices() -> List[Dict[str, object]]:
    """Fetch and cache Murf supported voices. Returns empty list on error."""
    global MURF_VOICES_CACHE
    if MURF_VOICES_CACHE:
        return MURF_VOICES_CACHE
    try:
        murf_api_key = os.getenv("MURF_API_KEY")
        if not murf_api_key:
            return []
        r = requests.get(
            "https://api.murf.ai/v1/speech/voices",
            headers={"api-key": murf_api_key, "Content-Type": "application/json"},
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
        # Murf returns list of voices; support both top-level list and {"voices": [...]} formats
        voices = data.get("voices") if isinstance(data, dict) else data
        if isinstance(voices, list):
            MURF_VOICES_CACHE = voices  # type: ignore[assignment]
        elif isinstance(data, list):
            MURF_VOICES_CACHE = data  # type: ignore[assignment]
        else:
            MURF_VOICES_CACHE = []
    except Exception as e:
        print(f"[MURF] Failed to fetch voices: {e}", flush=True)
        MURF_VOICES_CACHE = []
    return MURF_VOICES_CACHE

def resolve_murf_voice_id(desired_voice_id: str) -> str:
    """Validate desired voice id against Murf list, fallback to env/default valid voice.

    Order of resolution:
      1) If desired_voice_id exists in supported set → use it
      2) If MURF_VOICE_ID env exists and valid → use it
      3) Use 'en-US-terrell' if valid
      4) Use first available en-US voice if any
      5) Fall back to desired_voice_id (let API error surface if nothing else works)
    """
    voices = fetch_murf_voices()
    def extract_id(v: Dict[str, object]) -> str:
        # Voice objects may have 'voiceId' or 'id'
        if isinstance(v.get("voiceId"), str):  # type: ignore[call-arg]
            return str(v.get("voiceId"))
        if isinstance(v.get("id"), str):  # type: ignore[call-arg]
            return str(v.get("id"))
        return ""

    supported_ids = {extract_id(v) for v in voices if isinstance(v, dict)}

    # If we couldn't fetch voices, still prefer env default or a known-safe default
    if not supported_ids:
        env_default = os.getenv("MURF_VOICE_ID", "")
        if env_default:
            print(f"[MURF] Voices unavailable. Using env default '{env_default}'.", flush=True)
            return env_default
        print("[MURF] Voices unavailable. Falling back to 'en-US-terrell'.", flush=True)
        return "en-US-terrell"

    if desired_voice_id in supported_ids:
        return desired_voice_id

    env_default = os.getenv("MURF_VOICE_ID", "")
    if env_default and env_default in supported_ids:
        print(f"[MURF] Desired voice '{desired_voice_id}' invalid. Using env default '{env_default}'.", flush=True)
        return env_default

    if "en-US-terrell" in supported_ids:
        print(f"[MURF] Desired voice '{desired_voice_id}' invalid. Falling back to 'en-US-terrell'.", flush=True)
        return "en-US-terrell"

    # First available en-US voice if present
    for v in voices:
        if not isinstance(v, dict):
            continue
        lang = str(v.get("language", v.get("locale", ""))).lower()
        vid = extract_id(v)
        if vid and ("en-us" in lang or lang.startswith("en")):
            print(f"[MURF] Fallback to first EN voice '{vid}'.", flush=True)
            return vid

    print(f"[MURF] No valid fallback found; using requested id '{desired_voice_id}' (may error).", flush=True)
    return desired_voice_id

async def stream_text_to_murf_websocket(text: str, websocket_client=None, client_loop=None, session_id: str = None) -> None:
    """
    Stream text to Murf WebSocket API and receive base64 encoded audio.
    Day 21: Stream base64 audio chunks to client WebSocket in real-time.
    Day 24: Use persona-specific voice based on session.
    """
    murf_api_key = os.getenv("MURF_API_KEY")
    if not murf_api_key:
        print("[MURF] API key not configured, skipping TTS", flush=True)
        return

    # Day 24: Get persona-specific voice and resolve to a valid Murf voice id
    persona_id = SESSION_PERSONAS.get(session_id, "robot") if session_id else "robot"
    desired_voice_id = PERSONAS.get(persona_id, PERSONAS["robot"])["voice_id"]
    murf_voice_id = resolve_murf_voice_id(desired_voice_id)
    print(
        f"[MURF] Using persona '{persona_id}' with voice '{murf_voice_id}' (requested '{desired_voice_id}')",
        flush=True,
    )
    
    # Murf WebSocket URL with static context_id
    ws_url = f"wss://api.murf.ai/v1/speech/stream-input?api-key={murf_api_key}&sample_rate=44100&channel_type=MONO&format=WAV&context_id={MURF_CONTEXT_ID}"
    
    def send_to_client_safe(message: str) -> None:
        """Safely send message to client WebSocket if available"""
        if websocket_client:
            try:
                # Use asyncio to send message in a thread-safe way to the server loop
                target_loop = client_loop or asyncio.get_event_loop()
                asyncio.run_coroutine_threadsafe(websocket_client.send_text(message), target_loop)
            except Exception as e:
                print(f"[CLIENT] Failed to send to client: {e}", flush=True)
    
    try:
        print(f"[MURF] Connecting to WebSocket for TTS conversion...", flush=True)
        send_to_client_safe("audio_start:Starting TTS conversion...")
        
        async with websockets.connect(ws_url) as murf_ws:
            print(f"[MURF] Connected successfully", flush=True)
            send_to_client_safe("audio_status:Connected to Murf TTS")
            
            # Send voice configuration
            voice_config_msg = {
                "voice_config": {
                    "voiceId": murf_voice_id,
                    "style": "Conversational",
                    "rate": 0,
                    "pitch": 0,
                    "variation": 1
                }
            }
            await murf_ws.send(json.dumps(voice_config_msg))
            print(f"[MURF] Voice config sent: {murf_voice_id}", flush=True)
            
            # Send text for TTS conversion
            text_msg = {
                "text": text,
                "end": True
            }
            await murf_ws.send(json.dumps(text_msg))
            print(f"[MURF] Text sent for conversion: {text[:100]}...", flush=True)
            send_to_client_safe("audio_status:Text sent for TTS conversion")
            
            # Receive base64 encoded audio chunks and stream to client
            audio_chunks = []
            chunk_count = 0
            while True:
                try:
                    response = await murf_ws.recv()
                    data = json.loads(response)
                    
                    if "audio" in data:
                        audio_chunk = data["audio"]
                        audio_chunks.append(audio_chunk)
                        chunk_count += 1
                        
                        # Day 21: Stream base64 audio chunk to client
                        send_to_client_safe(f"audio_chunk:{audio_chunk}")
                        print(f"[MURF] Streamed audio chunk #{chunk_count} to client (length: {len(audio_chunk)})", flush=True)
                    
                    if data.get("isFinalAudio", False):
                        print(f"[MURF] Final audio received, total chunks: {len(audio_chunks)}", flush=True)
                        send_to_client_safe(f"audio_complete:{len(audio_chunks)}")
                        break
                        
                except websockets.exceptions.ConnectionClosed:
                    print("[MURF] WebSocket connection closed", flush=True)
                    send_to_client_safe("audio_error:Murf WebSocket connection closed")
                    break
                except Exception as e:
                    print(f"[MURF] Error receiving audio: {e}", flush=True)
                    send_to_client_safe(f"audio_error:Error receiving audio: {e}")
                    break
            
            # Combine all audio chunks and print final base64 (for Day 20 compatibility)
            if audio_chunks:
                combined_audio = "".join(audio_chunks)
                print(f"[MURF] COMPLETE BASE64 ENCODED AUDIO: {combined_audio}", flush=True)
                print(f"[MURF] Audio length: {len(combined_audio)} characters", flush=True)
            else:
                print("[MURF] No audio chunks received", flush=True)
                send_to_client_safe("audio_error:No audio chunks received")
                
    except Exception as e:
        print(f"[MURF] WebSocket connection failed: {e}", flush=True)
        send_to_client_safe(f"audio_error:WebSocket connection failed: {e}")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    # Normalize detail to an object with message
    if isinstance(detail, str):
        detail_obj: Dict[str, str] = {"message": detail}
    elif isinstance(detail, dict):
        detail_obj = detail  # type: ignore[assignment]
    else:
        detail_obj = {"message": str(detail)}

    # Ensure success flag and fallback text present
    content: Dict[str, object] = {
        "success": False,
        "detail": detail_obj,
        "fallback_text": FALLBACK_TEXT,
    }
    return JSONResponse(status_code=exc.status_code, content=content)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    content = {
        "success": False,
        "detail": {"message": f"Unhandled server error: {exc}"},
        "fallback_text": FALLBACK_TEXT,
    }
    return JSONResponse(status_code=500, content=content)


# Dev: prevent aggressive caching of static assets to ensure latest UI
@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/static/") or path.endswith(".css") or path.endswith(".js"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main HTML page"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "30 Days of AI - Day 20 is running!"}


@app.get("/api/day")
async def get_day_info():
    """Get information about the current day"""
    return {
        "day": 27,
        "title": "Revamp UI and Code Cleanup",
        "description": "User-configurable API keys, UI polish, and code cleanup for voice agent."
    }
@app.get("/api/config/{session_id}/keys")
async def get_session_keys(session_id: str):
    """Return which keys are set for this session (mask actual values)."""
    stored = USER_API_KEYS.get(session_id, {})
    return {
        "session_id": session_id,
        "keys": {k: (k in stored and bool(stored.get(k))) for k in ALLOWED_CONFIG_KEYS},
        "model": stored.get("GEMINI_MODEL") or os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        "murf_voice_id": stored.get("MURF_VOICE_ID") or os.getenv("MURF_VOICE_ID", "en-US-terrell"),
    }


class UpdateKeysRequest(BaseModel):
    keys: Dict[str, str]


@app.post("/api/config/{session_id}/keys")
async def update_session_keys(session_id: str, req: UpdateKeysRequest):
    """Store user-provided API keys for the session (in-memory)."""
    if not isinstance(req.keys, dict):
        raise HTTPException(status_code=400, detail="Invalid keys payload")
    filtered: Dict[str, str] = {k: v for k, v in req.keys.items() if k in ALLOWED_CONFIG_KEYS and isinstance(v, str) and v.strip()}
    if session_id not in USER_API_KEYS:
        USER_API_KEYS[session_id] = {}
    USER_API_KEYS[session_id].update(filtered)
    # Return which keys are set
    return {
        "success": True,
        "session_id": session_id,
        "keys": {k: (k in USER_API_KEYS[session_id]) for k in ALLOWED_CONFIG_KEYS},
    }



@app.get("/api/personas")
async def get_personas():
    """Get all available personas"""
    return {"personas": PERSONAS}


@app.post("/api/personas/{session_id}/{persona_id}")
async def set_persona(session_id: str, persona_id: str):
    """Set persona for a session"""
    if persona_id not in PERSONAS:
        raise HTTPException(status_code=400, detail=f"Invalid persona: {persona_id}")
    
    SESSION_PERSONAS[session_id] = persona_id
    return {
        "success": True,
        "session_id": session_id,
        "persona": PERSONAS[persona_id]
    }


@app.get("/api/personas/{session_id}")
async def get_session_persona(session_id: str):
    """Get current persona for a session"""
    persona_id = SESSION_PERSONAS.get(session_id, "robot")  # Default to robot
    return {
        "session_id": session_id,
        "persona_id": persona_id,
        "persona": PERSONAS[persona_id]
    }


# ------------------ Day 2: TTS Endpoint ------------------

class TTSRequest(BaseModel):
    text: str


@app.post("/api/tts/generate")
async def generate_tts(request: TTSRequest):
    """
    Generate TTS audio using Murf AI REST API and return the URL of the generated audio.
    """
    murf_api_key = get_user_config(None, "MURF_API_KEY")
    if not murf_api_key:
        raise HTTPException(
            status_code=500, detail="Murf API key not configured.")

    murf_endpoint = "https://api.murf.ai/v1/speech/generate"
    payload = {
        "text": request.text,
        "voiceId": "en-US-terrell",  # Corrected to camelCase: voiceId
    }
    headers = {
        "api-key": murf_api_key,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            murf_endpoint, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        audio_url = data.get("audioFile")  # Corrected to camelCase: audioFile
        if not audio_url:
            return {"success": False, "message": "No audio URL in Murf response", "raw_response": data, "fallback_text": FALLBACK_TEXT}
        return {"success": True, "audio_url": audio_url}
    except requests.RequestException as exc:
        error_detail = f"Failed to call Murf API: {exc}"
        if exc.response is not None:
            try:
                # Try to parse the JSON error response from Murf
                murf_error = exc.response.json()
                error_detail = f"Murf API Error: {murf_error.get('message', exc.response.text)}"
            except ValueError:
                # If response is not JSON, use the raw text
                error_detail = f"Murf API Error: {exc.response.status_code} - {exc.response.text}"
        raise HTTPException(status_code=502, detail=error_detail)

# ---------------------------------------------------------


# ------------------ Day 5: Audio Upload Endpoint ------------------
@app.post("/api/audio/upload")
async def upload_audio(file: UploadFile = File(...)):
    """
    Receive an audio file, save it temporarily, and return its details.
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file sent.")

    file_path = os.path.join(UPLOADS_DIR, file.filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = os.path.getsize(file_path)

        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "size": file_size
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save file: {e}")
# ------------------ Day 6: Transcription Endpoint ------------------

@app.post("/transcribe/file")
async def transcribe_file(file: UploadFile = File(...)):
    """Transcribe an uploaded audio file using AssemblyAI and return the text."""
    assemblyai_api_key = get_user_config(None, "ASSEMBLYAI_API_KEY")
    if not assemblyai_api_key:
        raise HTTPException(status_code=500, detail="AssemblyAI API key not configured.")
    try:
        aai.settings.api_key = assemblyai_api_key
        audio_bytes = await file.read()
        transcriber = aai.Transcriber()

        # Try to use the modern SDK helper for uploading bytes first. If the current
        # SDK version doesn't have that helper, fall back to passing the bytes
        # directly to the transcribe() method (supported by newer SDKs as well).
        try:
            upload_url = transcriber.upload_file(audio_bytes)  # type: ignore[attr-defined]
            transcript = transcriber.transcribe(upload_url)
        except AttributeError:
            # Older SDK – upload helper not available, pass raw bytes directly.
            transcript = transcriber.transcribe(audio_bytes)

        return {"transcript": transcript.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")

# ---------------------------------------------------------


# ------------------ Day 7: Echo Bot v2 (Transcribe -> Murf TTS) ------------------
@app.post("/tts/echo")
async def tts_echo(file: UploadFile = File(...)):
    """Accept audio, transcribe with AssemblyAI, synthesize with Murf, return audio URL."""
    assemblyai_api_key = get_user_config(None, "ASSEMBLYAI_API_KEY")
    murf_api_key = get_user_config(None, "MURF_API_KEY")

    if not assemblyai_api_key:
        raise HTTPException(status_code=500, detail="AssemblyAI API key not configured.")
    if not murf_api_key:
        raise HTTPException(status_code=500, detail="Murf API key not configured.")

    try:
        # 1) Transcribe using AssemblyAI
        aai.settings.api_key = assemblyai_api_key
        audio_bytes = await file.read()
        transcriber = aai.Transcriber()

        try:
            upload_url = transcriber.upload_file(audio_bytes)  # type: ignore[attr-defined]
            transcript = transcriber.transcribe(upload_url)
        except AttributeError:
            transcript = transcriber.transcribe(audio_bytes)

        transcript_text = transcript.text or ""
        if not transcript_text.strip():
            return {"success": False, "message": "No transcription text produced.", "fallback_text": FALLBACK_TEXT}

        # 2) Generate TTS using Murf
        murf_endpoint = "https://api.murf.ai/v1/speech/generate"
        payload = {
            "text": transcript_text,
            # Use any valid Murf voice; can be customized via env later
            "voiceId": os.getenv("MURF_VOICE_ID", "en-US-terrell"),
        }
        headers = {
            "api-key": murf_api_key,
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(murf_endpoint, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            data = response.json()
            audio_url = data.get("audioFile")
            if not audio_url:
                return {
                    "success": False,
                    "message": "No audio URL in Murf response",
                    "raw_response": data,
                    "transcript": transcript_text,
                    "fallback_text": FALLBACK_TEXT,
                }
            return {"success": True, "audio_url": audio_url, "transcript": transcript_text}
        except requests.RequestException as exc:
            error_detail = f"Failed to call Murf API: {exc}"
            if exc.response is not None:
                try:
                    murf_error = exc.response.json()
                    error_detail = f"Murf API Error: {murf_error.get('message', exc.response.text)}"
                except ValueError:
                    error_detail = f"Murf API Error: {exc.response.status_code} - {exc.response.text}"
            raise HTTPException(status_code=502, detail=error_detail)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Echo TTS failed: {e}")

# -------------------------------------------------------------------------------


# ------------------ Day 8 & 9: LLM Query Endpoint (text or audio) ------------------
class LLMQueryRequest(BaseModel):
    text: str
    model: Optional[str] = None  # Optional override, defaults via env or sensible default


@app.post("/llm/query")
async def llm_query(request: Request, file: Optional[UploadFile] = File(None), model: Optional[str] = Form(None)):
    """
    Accepts either:
    - JSON: { "text": "...", "model": "..." } → calls Gemini and returns generated text
    - multipart/form-data with 'file': audio blob (and optional 'model') → transcribe → Gemini → Murf → returns audio URL
    """
    session_id_from_query = request.query_params.get("session")
    gemini_api_key = get_user_config(session_id_from_query, "GEMINI_API_KEY")
    if not gemini_api_key:
        raise HTTPException(status_code=500, detail="Gemini API key not configured.")

    content_type = request.headers.get("content-type", "")

    # If audio is provided (multipart), run the full pipeline: Transcribe → LLM → Murf
    if "multipart/form-data" in content_type or file is not None:
        assemblyai_api_key = get_user_config(session_id_from_query, "ASSEMBLYAI_API_KEY")
        murf_api_key = get_user_config(session_id_from_query, "MURF_API_KEY")
        if not assemblyai_api_key:
            raise HTTPException(status_code=500, detail={"message": "AssemblyAI API key not configured.", "stage": "STT"})
        if not murf_api_key:
            raise HTTPException(status_code=500, detail={"message": "Murf API key not configured.", "stage": "TTS"})

        if file is None:
            raise HTTPException(status_code=400, detail="'file' is required in multipart form data.")

        # 1) Transcribe audio
        try:
            aai.settings.api_key = assemblyai_api_key
            audio_bytes = await file.read()
            transcriber = aai.Transcriber()

            try:
                upload_url = transcriber.upload_file(audio_bytes)  # type: ignore[attr-defined]
                transcript = transcriber.transcribe(upload_url)
            except AttributeError:
                transcript = transcriber.transcribe(audio_bytes)

            transcript_text = (transcript.text or "").strip()
            if not transcript_text:
                return {"success": False, "message": "No transcription text produced.", "fallback_text": FALLBACK_TEXT}
        except Exception as e:
            raise HTTPException(status_code=500, detail={"message": f"Transcription failed: {e}", "stage": "STT"})

        # 2) Query Gemini with transcribed text
        chosen_model = model or get_user_config(session_id_from_query, "GEMINI_MODEL", "gemini-1.5-flash")
        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{chosen_model}:generateContent?key={gemini_api_key}"
        )
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": transcript_text}
                    ]
                }
            ]
        }
        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()

            llm_text = ""
            candidates = data.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts and isinstance(parts[0], dict):
                    llm_text = parts[0].get("text", "")

            if not llm_text:
                return {
                    "success": False,
                    "message": "No generated text returned by Gemini",
                    "raw_response": data,
                    "transcript": transcript_text,
                    "fallback_text": FALLBACK_TEXT,
                }
        except requests.RequestException as exc:
            error_detail = f"Failed to call Gemini API: {exc}"
            if exc.response is not None:
                try:
                    gemini_error = exc.response.json()
                    if isinstance(gemini_error, dict) and "error" in gemini_error:
                        error_detail = f"Gemini API Error: {gemini_error['error']}"
                    else:
                        error_detail = f"Gemini API Error: {gemini_error}"
                except ValueError:
                    error_detail = f"Gemini API Error: {exc.response.status_code} - {exc.response.text}"
            raise HTTPException(status_code=502, detail={"message": error_detail, "stage": "LLM"})

        
        murf_text = llm_text[:3000]
        murf_endpoint = "https://api.murf.ai/v1/speech/generate"
        murf_payload = {
            "text": murf_text,
            "voiceId": os.getenv("MURF_VOICE_ID", "en-US-terrell"),
        }
        murf_headers = {
            "api-key": murf_api_key,
            "Content-Type": "application/json",
        }
        try:
            tts_response = requests.post(
                murf_endpoint, json=murf_payload, headers=murf_headers, timeout=60
            )
            tts_response.raise_for_status()
            tts_data = tts_response.json()
            audio_url = tts_data.get("audioFile")
            if not audio_url:
                return {
                    "success": False,
                    "message": "No audio URL in Murf response",
                    "raw_response": tts_data,
                    "transcript": transcript_text,
                    "llm_text": llm_text,
                    "fallback_text": FALLBACK_TEXT,
                }
            return {
                "success": True,
                "model": chosen_model,
                "audio_url": audio_url,
                "transcript": transcript_text,
                "llm_text": llm_text,
                "truncated_for_tts": len(llm_text) > 3000,
            }
        except requests.RequestException as exc:
            error_detail = f"Failed to call Murf API: {exc}"
            if exc.response is not None:
                try:
                    murf_error = exc.response.json()
                    error_detail = f"Murf API Error: {murf_error.get('message', exc.response.text)}"
                except ValueError:
                    error_detail = f"Murf API Error: {exc.response.status_code} - {exc.response.text}"
            raise HTTPException(status_code=502, detail={"message": error_detail, "stage": "TTS"})

    # Else: JSON (text → LLM only)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail={"message": "Expected JSON body or multipart form data with 'file'."})

    try:
        parsed = LLMQueryRequest(**body)
    except Exception as e:
        raise HTTPException(status_code=400, detail={"message": f"Invalid request body: {e}"})

    prompt_text = (parsed.text or "").strip()
    if not prompt_text:
        raise HTTPException(status_code=400, detail={"message": "'text' is required and cannot be empty."})

    chosen_model = parsed.model or get_user_config(session_id_from_query, "GEMINI_MODEL", "gemini-1.5-flash")
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{chosen_model}:generateContent?key={gemini_api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt_text}
                ]
            }
        ]
    }

    try:
        response = requests.post(endpoint, json=payload, headers={"Content-Type": "application/json"}, timeout=60)
        response.raise_for_status()
        data = response.json()

        generated_text = ""
        candidates = data.get("candidates", [])
        if candidates:
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if parts and isinstance(parts[0], dict):
                generated_text = parts[0].get("text", "")

        if not generated_text:
            return {
                "success": False,
                "message": "No generated text returned by Gemini",
                "raw_response": data,
                "fallback_text": FALLBACK_TEXT,
            }

        return {"success": True, "model": chosen_model, "response": generated_text}
    except requests.RequestException as exc:
        error_detail = f"Failed to call Gemini API: {exc}"
        if exc.response is not None:
            try:
                gemini_error = exc.response.json()
                if isinstance(gemini_error, dict) and "error" in gemini_error:
                    error_detail = f"Gemini API Error: {gemini_error['error']}"
                else:
                    error_detail = f"Gemini API Error: {gemini_error}"
            except ValueError:
                error_detail = f"Gemini API Error: {exc.response.status_code} - {exc.response.text}"
        raise HTTPException(status_code=502, detail={"message": error_detail, "stage": "LLM"})


# ------------------ Day 10: Agent Chat with Session History ------------------
@app.post("/agent/chat/{session_id}")
async def agent_chat(session_id: str, file: Optional[UploadFile] = File(None), model: Optional[str] = Form(None)):
    """
    Accepts audio (multipart) and maintains chat history per session.
    Pipeline: STT (AssemblyAI) → build context from history+new user message → LLM (Gemini) → store reply → TTS (Murf) → return audio.
    """
    # Simulate credit exhaustion: return a structured error like a real backend failure
    if SIMULATE_CREDIT_EXHAUSTION:
        raise HTTPException(status_code=402, detail={"message": "Sorry the api credit has been exhausted", "code": "credit_exhausted"})
    assemblyai_api_key = get_user_config(session_id, "ASSEMBLYAI_API_KEY")
    gemini_api_key = get_user_config(session_id, "GEMINI_API_KEY")
    murf_api_key = get_user_config(session_id, "MURF_API_KEY")

    if not assemblyai_api_key:
        raise HTTPException(status_code=500, detail={"message": "AssemblyAI API key not configured.", "stage": "STT"})
    if not gemini_api_key:
        raise HTTPException(status_code=500, detail={"message": "Gemini API key not configured.", "stage": "LLM"})
    if not murf_api_key:
        raise HTTPException(status_code=500, detail={"message": "Murf API key not configured.", "stage": "TTS"})

    if file is None:
        raise HTTPException(status_code=400, detail="'file' is required in multipart form data.")

    # 1) Transcribe audio to text
    try:
        aai.settings.api_key = assemblyai_api_key
        audio_bytes = await file.read()
        transcriber = aai.Transcriber()

        try:
            upload_url = transcriber.upload_file(audio_bytes)  # type: ignore[attr-defined]
            transcript = transcriber.transcribe(upload_url)
        except AttributeError:
            transcript = transcriber.transcribe(audio_bytes)

        user_message = (transcript.text or "").strip()
        if not user_message:
            return {"success": False, "message": "No transcription text produced.", "fallback_text": FALLBACK_TEXT}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"message": f"Transcription failed: {e}", "stage": "STT"})

    # 2) Retrieve chat history and build Gemini contents with persona context
    history = CHAT_SESSIONS.get(session_id, [])
    chosen_model = model or get_user_config(session_id, "GEMINI_MODEL", "gemini-1.5-flash")
    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{chosen_model}:generateContent?key={gemini_api_key}"
    )

    # Day 24: Get persona and build system message
    persona_id = SESSION_PERSONAS.get(session_id, "robot")
    persona = PERSONAS.get(persona_id, PERSONAS["robot"])
    system_prompt = persona["system_prompt"]

    # Convert our simple history to Gemini 'contents' with persona context
    contents = []
    
    # Add persona context if this is the start of conversation
    if not history:
        contents.append({
            "role": "user",
            "parts": [{"text": f"SYSTEM: {system_prompt}\n\nPlease acknowledge you understand your role and are ready to help."}]
        })
        contents.append({
            "role": "model", 
            "parts": [{"text": f"I understand! I am {persona['name']} and I'm ready to help you in character. How may I assist you today?"}]
        })
    
    # Add chat history
    for msg in history:
        role = "user" if msg.get("role") == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg.get("text", "")}]} )
    
    # Append current user message
    contents.append({"role": "user", "parts": [{"text": user_message}]})

    payload = {"contents": contents}

    # 3) Call Gemini with function calling capability
    try:
        gemini_api_key = get_user_config(session_id, "GEMINI_API_KEY")
        if not gemini_api_key:
            raise HTTPException(status_code=500, detail={"message": "Gemini API key not configured.", "stage": "LLM"})
        
        # Use per-request function calling service with Tavily key override
        fcs = FunctionCallingService()
        fcs.set_tavily_api_key_override(get_user_config(session_id, "TAVILY_API_KEY"))
        function_result = fcs.call_gemini_with_functions(
            contents, gemini_api_key, chosen_model
        )
        
        if not function_result.get("success"):
            return {
                "success": False,
                "message": f"Function calling failed: {function_result.get('error', 'Unknown error')}",
                "transcript": user_message,
                "fallback_text": FALLBACK_TEXT,
                "function_calls": function_result.get("function_calls", [])
            }
        
        llm_text = function_result.get("response", "")
        function_calls_made = function_result.get("function_calls", [])
        
        if not llm_text:
            return {
                "success": False,
                "message": "No generated text returned by Gemini with function calling",
                "transcript": user_message,
                "fallback_text": FALLBACK_TEXT,
                "function_calls": function_calls_made
            }
            
        # Log function calls made
        if function_calls_made:
            print(f"[AGENT_CHAT] Function calls made: {len(function_calls_made)}")
            for i, call in enumerate(function_calls_made):
                print(f"[AGENT_CHAT] Call {i+1}: {call.get('function_name', 'unknown')} - Success: {call.get('success', False)}")
        
    except Exception as exc:
        error_detail = f"Failed to call Gemini API with function calling: {exc}"
        raise HTTPException(status_code=502, detail={"message": error_detail, "stage": "LLM"})

    # 4) Update chat history (append user and model messages)
    updated_history = history + [
        {"role": "user", "text": user_message},
        {"role": "model", "text": llm_text},
    ]
    CHAT_SESSIONS[session_id] = updated_history

    # 5) TTS via Murf (truncate to 3000 chars per requirements) with persona voice
    murf_text = llm_text[:3000]
    murf_endpoint = "https://api.murf.ai/v1/speech/generate"
    
    # Use persona-specific voice with validation/fallback
    persona_voice = resolve_murf_voice_id(persona["voice_id"])
    murf_payload = {
        "text": murf_text,
        "voiceId": persona_voice,
    }
    murf_headers = {
        "api-key": murf_api_key,
        "Content-Type": "application/json",
    }
    try:
        tts_response = requests.post(
            murf_endpoint, json=murf_payload, headers=murf_headers, timeout=60
        )
        tts_response.raise_for_status()
        tts_data = tts_response.json()
        audio_url = tts_data.get("audioFile")
        if not audio_url:
            return {
                "success": False,
                "message": "No audio URL in Murf response",
                "raw_response": tts_data,
                "transcript": user_message,
                "llm_text": llm_text,
                "fallback_text": FALLBACK_TEXT,
            }
        return {
            "success": True,
            "model": chosen_model,
            "audio_url": audio_url,
            "transcript": user_message,
            "llm_text": llm_text,
            "truncated_for_tts": len(llm_text) > 3000,
            "history_len": len(CHAT_SESSIONS.get(session_id, [])),
            "function_calls": function_calls_made,
            "web_search_used": any(call.get("function_name") == "search_web" for call in function_calls_made)
        }
    except requests.RequestException as exc:
        error_detail = f"Failed to call Murf API: {exc}"
        if exc.response is not None:
            try:
                murf_error = exc.response.json()
                error_detail = f"Murf API Error: {murf_error.get('message', exc.response.text)}"
            except ValueError:
                error_detail = f"Murf API Error: {exc.response.status_code} - {exc.response.text}"
        raise HTTPException(status_code=502, detail={"message": error_detail, "stage": "TTS"})


@app.get("/agent/chat/{session_id}/history")
async def get_chat_history(session_id: str):
    """Return chat history for the session."""
    history = CHAT_SESSIONS.get(session_id, [])
    return {"session_id": session_id, "messages": history, "count": len(history)}

# ---------------------------------------------------------------


# ------------------ Day 15: WebSocket Echo Endpoint ------------------
@app.websocket("/ws")
async def websocket_echo(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_text()
            await websocket.send_text(f"echo: {message}")
    except WebSocketDisconnect:
        # Client disconnected; simply end the connection handler
        pass


# ------------------ Day 16: Streaming Audio over WebSocket ------------------
@app.websocket("/ws/audio")
async def websocket_audio_stream(websocket: WebSocket):
    """Receive binary audio data frames over a WebSocket and save to a .webm file."""
    await websocket.accept()

    # Generate a unique filename per connection
    filename = f"recording-{datetime.utcnow().strftime('%Y%m%d-%H%M%S-%f')}.webm"
    file_path = os.path.join(UPLOADS_DIR, filename)

    # Open the destination file and stream-append incoming binary chunks
    with open(file_path, "wb") as f:
        try:
            while True:
                message = await websocket.receive()
                data_bytes = message.get("bytes")
                data_text = message.get("text")

                if data_bytes is not None:
                    f.write(data_bytes)
                    f.flush()
                elif data_text is not None:
                    # Optional control message from client to end recording
                    if data_text.lower() == "done":
                        break
        except WebSocketDisconnect:
            # Client disconnected; finalize file
            pass
        except Exception as exc:
            # Best-effort notify client of error, then close
            try:
                await websocket.send_text(f"error: {exc}")
            except Exception:
                pass
        finally:
            try:
                await websocket.send_text(f"saved:{filename}")
            except Exception:
                pass
            try:
                await websocket.close()
            except Exception:
                pass


# ------------------ Day 17: WebSocket → AssemblyAI Universal Streaming Transcription ------------------
@app.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    """Receive 16kHz, 16-bit mono PCM audio frames and stream to AssemblyAI Universal Streaming for realtime transcription.

    Sends back messages like:
      - "partial:<text>"
      - "final:<text>"
      - "error:<message>"
    and also prints transcripts on the server console.
    """
    await websocket.accept()
    # Simulate credit exhaustion: immediately notify client and close
    if SIMULATE_CREDIT_EXHAUSTION:
        try:
            await websocket.send_text("error:Sorry the api credit has been exhausted")
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass
        return

    # Session id for per-session config
    try:
        session_id = websocket.query_params.get("session")  # type: ignore[attr-defined]
    except Exception:
        session_id = None

    assemblyai_api_key = get_user_config(session_id, "ASSEMBLYAI_API_KEY")
    if not assemblyai_api_key:
        await websocket.send_text("error:AssemblyAI API key not configured")
        await websocket.close()
        return

    # Day 19: Gemini streaming configuration
    gemini_api_key = get_user_config(session_id, "GEMINI_API_KEY")
    gemini_model = get_user_config(session_id, "GEMINI_MODEL", "gemini-1.5-flash")

    # Import the new Universal Streaming API (v3)
    try:
        from assemblyai.streaming.v3 import (
            StreamingClient,
            StreamingClientOptions,
            StreamingParameters,
            StreamingEvents,
            TurnEvent,
        )
    except ImportError as e:
        await websocket.send_text(f"error:Universal Streaming API not available: {e}")
        await websocket.close()
        return

    loop = asyncio.get_running_loop()
    # Track latest transcripts and whether LLM streaming has started
    last_final_transcript: Dict[str, Optional[str]] = {"value": None}
    last_seen_transcript: Dict[str, Optional[str]] = {"value": None}
    llm_started: Dict[str, bool] = {"value": False}

    def send_text_threadsafe(message: str) -> None:
        try:
            asyncio.run_coroutine_threadsafe(websocket.send_text(message), loop)
        except Exception:
            pass

    # Initialize the Universal Streaming client
    try:
        client = StreamingClient(
            options=StreamingClientOptions(api_key=assemblyai_api_key)
        )
        print("[AAI] Universal Streaming client created")
        send_text_threadsafe("partial:Connected to AssemblyAI Universal Streaming")
    except Exception as exc:
        await websocket.send_text(f"error:streaming_client_init_failed:{exc}")
        await websocket.close()
        return

    # Set up event handlers for Universal Streaming
    def on_partial(_client, event):
        # Handle partial transcripts (real-time updates)
        transcript = getattr(event, "transcript", None)
        if transcript:
            print(f"[AAI][partial] {transcript}", flush=True)
            send_text_threadsafe(f"partial:{transcript}")

    def stream_gemini_response(prompt_text: str, client_websocket=None) -> None:
        if not gemini_api_key:
            print("[LLM] GEMINI_API_KEY not configured; skipping streaming.", flush=True)
            return

        # Day 24: Get persona and build system message
        persona_id = SESSION_PERSONAS.get(session_id, "robot") if session_id else "robot"
        persona = PERSONAS.get(persona_id, PERSONAS["robot"])
        system_prompt = persona["system_prompt"]
        
        # Build conversation with persona context
        contents = []
        
        # Add system prompt as first user message (Gemini doesn't have system role)
        contents.append({
            "role": "user",
            "parts": [{"text": f"SYSTEM: {system_prompt}\n\nPlease acknowledge you understand your role and are ready to help."}]
        })
        
        # Add a model response acknowledging the role
        contents.append({
            "role": "model", 
            "parts": [{"text": f"I understand! I am {persona['name']} and I'm ready to help you in character. How may I assist you today?"}]
        })
        
        # Add current user message
        contents.append({
            "role": "user",
            "parts": [{"text": prompt_text}]
        })

        # Day 25: Try function calling first for better results
        try:
            print("[LLM] Attempting function calling for streaming response", flush=True)
            fcs = FunctionCallingService()
            fcs.set_tavily_api_key_override(get_user_config(session_id, "TAVILY_API_KEY"))
            function_result = fcs.call_gemini_with_functions(
                contents, gemini_api_key, gemini_model, max_function_calls=2
            )
            
            if function_result.get("success") and function_result.get("response"):
                full_text = function_result.get("response", "")
                function_calls_made = function_result.get("function_calls", [])
                
                print(f"[LLM] Function calling successful, got response: {full_text[:100]}...", flush=True)
                if function_calls_made:
                    print(f"[LLM] Function calls made: {len(function_calls_made)}")
                    for call in function_calls_made:
                        if call.get("function_name") == "search_web":
                            print(f"[LLM] Web search performed: {call.get('parameters', {}).get('query', 'unknown query')}")
                
                # Send the complete response
                send_text_threadsafe(f"assistant_text:{full_text}")
                
                # Persist to chat history
                try:
                    if session_id:
                        history = CHAT_SESSIONS.get(session_id, [])
                        updated_history = history + [
                            {"role": "user", "text": last_final_transcript.get("value") or prompt_text},
                            {"role": "model", "text": full_text},
                        ]
                        CHAT_SESSIONS[session_id] = updated_history
                except Exception as hist_exc:
                    print(f"[HISTORY] Failed to persist function calling messages: {hist_exc}", flush=True)
                
                # Send to TTS
                try:
                    tts_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(tts_loop)
                    tts_loop.run_until_complete(stream_text_to_murf_websocket(full_text, client_websocket, client_loop=loop, session_id=session_id))
                    tts_loop.close()
                except Exception as murf_error:
                    print(f"[MURF] Failed to send function calling response to Murf WebSocket: {murf_error}", flush=True)
                return
            else:
                print(f"[LLM] Function calling failed or no response: {function_result.get('error', 'Unknown error')}", flush=True)
                
        except Exception as func_exc:
            print(f"[LLM] Function calling failed with exception: {func_exc}, falling back to streaming", flush=True)

        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:streamGenerateContent"
        )
        payload = {"contents": contents}

        try:
            print(f"[LLM] Streaming POST → model={gemini_model}", flush=True)
            with requests.post(
                endpoint,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": gemini_api_key,
                    "Accept": "text/event-stream",
                    "Connection": "keep-alive",
                },
                stream=True,
                timeout=300,
            ) as response:
                response.raise_for_status()
                print(f"[LLM] Streaming response status {response.status_code}", flush=True)
                accumulated_chunks: List[str] = []
                had_chunk = False
                debug_count = 0
                for raw_line in response.iter_lines(decode_unicode=True):
                    if not raw_line:
                        continue
                    line = raw_line.strip()
                    if not line:
                        continue
                    if debug_count < 5:
                        print(f"[LLM][raw] {line}", flush=True)
                        debug_count += 1
                    # Some servers may prefix with 'data:' like SSE
                    if line.startswith("data:"):
                        line = line[5:].strip()
                        if not line:
                            continue
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        # Some servers may send event lines that aren't JSON (e.g., comments)
                        continue

                    try:
                        candidates = item.get("candidates", [])
                        if candidates:
                            content = candidates[0].get("content", {})
                            parts = content.get("parts", [])
                            if parts and isinstance(parts[0], dict):
                                chunk_text = parts[0].get("text", "")
                                if chunk_text:
                                    accumulated_chunks.append(chunk_text)
                                    print(f"[LLM][chunk] {chunk_text}", flush=True)
                                    had_chunk = True
                            finish_reason = candidates[0].get("finishReason") or candidates[0].get("finish_reason")
                            if finish_reason:
                                print(f"[LLM][finish] {finish_reason}", flush=True)
                    except Exception:
                        # Ignore malformed interim items
                        pass

                full_text = "".join(accumulated_chunks)
                if full_text:
                    print(f"[LLM][full] {full_text}", flush=True)
                    # Day 21: Send complete LLM response to Murf WebSocket with client WebSocket
                    print("[MURF] Sending LLM response to Murf WebSocket for TTS conversion...", flush=True)
                    # Day 23: Immediately notify client with assistant text
                    try:
                        send_text_threadsafe(f"assistant_text:{full_text}")
                    except Exception:
                        pass
                    # Day 23: Persist to in-memory chat history if session_id present
                    try:
                        if session_id:
                            history = CHAT_SESSIONS.get(session_id, [])
                            updated_history = history + [
                                {"role": "user", "text": last_final_transcript.get("value") or prompt_text},
                                {"role": "model", "text": full_text},
                            ]
                            CHAT_SESSIONS[session_id] = updated_history
                    except Exception as hist_exc:
                        print(f"[HISTORY] Failed to persist streaming messages: {hist_exc}", flush=True)
                    try:
                        # Run Murf websocket in a separate event loop since we're in a thread
                        tts_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(tts_loop)
                        tts_loop.run_until_complete(stream_text_to_murf_websocket(full_text, client_websocket, client_loop=loop, session_id=session_id))
                        tts_loop.close()
                    except Exception as murf_error:
                        print(f"[MURF] Failed to send to Murf WebSocket: {murf_error}", flush=True)
                elif not had_chunk:
                    # Fallback: call non-streaming generateContent once
                    try:
                        fallback_endpoint = (
                            f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent"
                        )
                        fallback_payload = {
                            "contents": [
                                {
                                    "role": "user",
                                    "parts": [
                                        {"text": prompt_text}
                                    ]
                                }
                            ]
                        }
                        print("[LLM] No stream chunks; trying non-streaming fallback", flush=True)
                        r = requests.post(
                            fallback_endpoint,
                            json=fallback_payload,
                            headers={
                                "Content-Type": "application/json",
                                "x-goog-api-key": gemini_api_key,
                            },
                            timeout=60,
                        )
                        r.raise_for_status()
                        data = r.json()
                        print(f"[LLM][fallback_raw] {json.dumps(data)[:300]}...", flush=True)
                        candidates = data.get("candidates", [])
                        if candidates:
                            content = candidates[0].get("content", {})
                            parts = content.get("parts", [])
                            if parts and isinstance(parts[0], dict):
                                text = parts[0].get("text", "")
                                if text:
                                    print(f"[LLM][full-fallback] {text}", flush=True)
                                    # Day 23: Immediately notify client with assistant text (fallback)
                                    try:
                                        send_text_threadsafe(f"assistant_text:{text}")
                                    except Exception:
                                        pass
                                    # Day 23: Persist fallback full text as well
                                    try:
                                        if session_id:
                                            history = CHAT_SESSIONS.get(session_id, [])
                                            updated_history = history + [
                                                {"role": "user", "text": last_final_transcript.get("value") or prompt_text},
                                                {"role": "model", "text": text},
                                            ]
                                            CHAT_SESSIONS[session_id] = updated_history
                                    except Exception as hist_exc:
                                        print(f"[HISTORY] Failed to persist fallback messages: {hist_exc}", flush=True)
                                    # Day 21: Send fallback response to Murf WebSocket with client WebSocket
                                    try:
                                        tts_loop = asyncio.new_event_loop()
                                        asyncio.set_event_loop(tts_loop)
                                        tts_loop.run_until_complete(stream_text_to_murf_websocket(text, client_websocket, client_loop=loop, session_id=session_id))
                                        tts_loop.close()
                                    except Exception as murf_error:
                                        print(f"[MURF] Failed to send fallback to Murf WebSocket: {murf_error}", flush=True)
                    except Exception as e:
                        print(f"[LLM] Fallback failed: {e}", flush=True)
        except requests.RequestException as exc:
            print(f"[LLM] Streaming request failed: {exc}", flush=True)
    def on_turn(_client, event: TurnEvent):
        transcript = getattr(event, "transcript", None)
        is_end = getattr(event, "end_of_turn", True)
        if transcript:
            try:
                print(f"[AAI][turn] is_end={is_end} llm_started={llm_started['value']} len={len(transcript)}", flush=True)
            except Exception:
                pass
            last_seen_transcript["value"] = transcript
            last_final_transcript["value"] = transcript
            print(f"[AAI][final] {transcript}")
            send_text_threadsafe(f"final:{transcript}")
            # Day 18: Explicitly notify client of end of user turn with transcript
            if is_end:
                send_text_threadsafe(f"turn_end:{transcript}")
                # Day 19: Trigger Gemini streaming using the final transcript
                if not llm_started["value"]:
                    llm_started["value"] = True
                    print(f"[LLM] Starting streaming due to end-of-turn (model={gemini_model}, has_key={bool(gemini_api_key)})", flush=True)
                    try:
                        threading.Thread(target=stream_gemini_response, args=(transcript, websocket), daemon=True).start()
                    except Exception as exc:
                        print(f"[LLM] Failed to start streaming thread: {exc}", flush=True)
                else:
                    print("[LLM] Streaming already started; skipping duplicate trigger (end-of-turn)", flush=True)
            else:
                # If no explicit end-of-turn arrives, start once on first transcript
                if not llm_started["value"]:
                    llm_started["value"] = True
                    print(f"[LLM] Starting streaming on first transcript (no turn_end yet) (model={gemini_model}, has_key={bool(gemini_api_key)})", flush=True)
                    try:
                        threading.Thread(target=stream_gemini_response, args=(transcript, websocket), daemon=True).start()
                    except Exception as exc:
                        print(f"[LLM] Failed to start streaming thread: {exc}", flush=True)
                else:
                    print("[LLM] Streaming already started; skipping duplicate trigger (interim)", flush=True)

    # Register event handlers
    client.on(StreamingEvents.Turn, on_turn)
    try:
        # Try to register partial transcript handler if available
        from assemblyai.streaming.v3 import PartialTranscriptEvent
        client.on(StreamingEvents.PartialTranscript, on_partial)
        print("[AAI] Registered partial transcript handler", flush=True)
    except (ImportError, AttributeError):
        print("[AAI] Partial transcript handler not available", flush=True)

    # Connect in a background thread
    def connect_streaming():
        try:
            # Connect with Universal Streaming parameters
            client.connect(
                StreamingParameters(
                    sample_rate=16000,
                    format_turns=True,  # Enable turn events for final transcripts
                    # Add additional debugging parameters
                    enable_extra_session_information=True,
                )
            )
            print("[AAI] Universal Streaming connected")
        except Exception as exc:
            print(f"[AAI] Universal Streaming connect() failed: {exc}")
            send_text_threadsafe(f"error:connect_failed:{exc}")

    connect_thread = threading.Thread(target=connect_streaming, daemon=True)
    connect_thread.start()

    try:
        bytes_total: int = 0
        frames_total: int = 0
        while True:
            try:
                message = await websocket.receive()
            except RuntimeError:
                break  # Socket already disconnected

            data_bytes = message.get("bytes")
            data_text = message.get("text")

            if data_bytes is not None:
                # Forward raw PCM16LE 16k mono audio bytes to Universal Streaming
                try:
                    client.stream(data_bytes)
                    bytes_total += len(data_bytes)
                    frames_total += 1
                    if frames_total % 50 == 0:
                        print(f"[WS] forwarded frames={frames_total} bytes={bytes_total}", flush=True)
                except Exception as exc:
                    print(f"[AAI] stream() error: {exc}")
            elif data_text is not None:
                if data_text.lower() == "done":
                    print("[WS] Received 'done' from client", flush=True)
                    print(f"[WS] totals frames={frames_total} bytes={bytes_total}", flush=True)
                    # If client ends before we saw an explicit end-of-turn, fallback to last final transcript
                    if not llm_started["value"]:
                        # Prefer final transcript, else fall back to last seen partial transcript
                        fallback_text = last_final_transcript["value"] or last_seen_transcript["value"]
                        if fallback_text:
                            llm_started["value"] = True
                            print("[LLM] Starting streaming due to client 'done'", flush=True)
                            try:
                                threading.Thread(target=stream_gemini_response, args=(fallback_text, websocket), daemon=True).start()
                            except Exception as exc:
                                print(f"[LLM] Failed to start streaming thread: {exc}", flush=True)
                        else:
                            print("[DEBUG] No transcript received from AssemblyAI - trying test prompt", flush=True)
                            # Force trigger with test text to verify LLM streaming works
                            llm_started["value"] = True
                            try:
                                # Use a more interesting test prompt
                                test_prompt = "Explain what streaming LLM responses are in one sentence."
                                threading.Thread(target=stream_gemini_response, args=(test_prompt, websocket), daemon=True).start()
                            except Exception as exc:
                                print(f"[LLM] Failed to start streaming thread: {exc}", flush=True)
                    break
    except WebSocketDisconnect:
        pass
    finally:
        try:
            # Disconnect from Universal Streaming
            try:
                client.disconnect(terminate=True)
                print("[AAI] Universal Streaming disconnected")
            except Exception:
                pass
            await websocket.close()
        except Exception:
            pass

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
