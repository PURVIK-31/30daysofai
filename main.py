from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import os
import requests
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="30 Days of AI - Day 1", version="1.0.0")

# Mount static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates for HTML rendering
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main HTML page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "30 Days of AI - Day 1 is running!"}

@app.get("/api/day")
async def get_day_info():
    """Get information about the current day"""
    return {
        "day": 1,
        "title": "Project Setup",
        "description": "Initialize a Python backend using FastAPI and create a basic frontend"
    }

# ------------------ Day 2: TTS Endpoint ------------------

class TTSRequest(BaseModel):
    text: str

@app.post("/api/tts/generate")
async def generate_tts(request: TTSRequest):
    """
    Generate TTS audio using Murf AI REST API and return the URL of the generated audio.
    """
    murf_api_key = os.getenv("MURF_API_KEY")
    if not murf_api_key:
        raise HTTPException(status_code=500, detail="Murf API key not configured.")

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
        response = requests.post(murf_endpoint, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        audio_url = data.get("audioFile") # Corrected to camelCase: audioFile
        if not audio_url:
            return {"success": False, "message": "No audio URL in Murf response", "raw_response": data}
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 