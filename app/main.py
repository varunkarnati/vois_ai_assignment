# main.py (copied from canvas)
from fastapi import FastAPI, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware
import numpy as np
import soundfile as sf
import tempfile
import base64
import os
import asyncio
import logging

# Configure logging (optional)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.utils.stt import transcribe_audio
from app.utils.llm import ask_llm
from app.utils.tts import speak_text_stream

app = FastAPI()
from fastapi.staticfiles import StaticFiles
from pathlib import Path



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
from fastapi import UploadFile
from pydub import AudioSegment

@app.post("/api/audio")
async def handle_audio(file: UploadFile):
    logger.info(f"Received file: {file.filename}, content_type: {file.content_type}")
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp_path = tmp.name

        audio_segment = AudioSegment.from_file(tmp_path)  # Let pydub auto-detect
        wav_path = tmp_path.replace(".webm", ".wav")
        audio_segment.export(wav_path, format="wav")

        audio, sr = sf.read(wav_path)
        transcript = transcribe_audio(audio, sr)
        response = await ask_llm(transcript)
        audio_b64 = await speak_text_stream(response)

        os.remove(tmp_path)
        os.remove(wav_path)

        return { "transcript": transcript, "response": response, "audio": audio_b64 }

    except Exception as e:
        logger.error(f"Audio processing failed: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e)}, status_code=400)
@app.post("/api/start_conversation")
async def start_conversation():
    """
    Generates an initial greeting message and audio.
    """
    try:
        logger.info("Received request to start conversation.")
        # Option 1: Hardcoded greeting
        initial_greeting = "Hello! Welcome to our restaurant. How can I help you order today?"

        # Option 2: Use LLM for a dynamic greeting (if desired)
        # initial_greeting = await ask_llm("Greet the user and ask how you can help them order.")
        # logger.info(f"LLM generated greeting: {initial_greeting}")

        # Generate audio for the greeting
        audio_base64 = await speak_text_stream(initial_greeting)
        logger.info(f"Generated audio for greeting, base64 length: {len(audio_base64)}")

        if not audio_base64:
             logger.error("TTS failed to generate audio for initial greeting.")
             return JSONResponse(content={"error": "Failed to generate initial audio greeting"}, status_code=500)

        # Return the greeting text (as 'transcript' or a new field like 'response')
        # and the audio data (as 'audio')
        return {"transcript": initial_greeting, "response": initial_greeting, "audio": audio_base64} # Send text as both for now

    except Exception as e:
        logger.error(f"Error in /api/start_conversation: {e}", exc_info=True)
        return JSONResponse(content={"error": "Internal server error starting conversation"}, status_code=500)
@app.get("/api/signed_url/{agent_id}")
async def signed_url(agent_id: str):
    try:
        from elevenlabs import ElevenLabs
        client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
        signed = client.conversational_ai.get_signed_url(agent_id=agent_id)
        return {"signedUrl": signed}
    except Exception as e:
        logger.error(f"Signed URL error: {e}")
        return JSONResponse(content={"error": "Failed to generate signed URL"}, status_code=500)

from uuid import uuid4
from uuid import uuid4

@app.websocket("/ws/converse")
async def converse_websocket(websocket: WebSocket):
    await websocket.accept()
    order_id = str(uuid4())[:4]
    logger.info(f"New session started with order_id: {order_id}")

    initial_greeting = "Hello! Welcome to our restaurant. How can I help you order today?"
    audio_base64 = await speak_text_stream(initial_greeting)
    await websocket.send_json({
        "orderId": order_id,
        "transcript": initial_greeting,
        "response": initial_greeting,
        "audio": audio_base64,
        "order": {
            "items": [],
            "total": 0.0
        }
    })

    try:
        while True:
            data = await websocket.receive_bytes()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(data)
                tmp_path = tmp.name

            audio, sr = sf.read(tmp_path)
            transcript = transcribe_audio(audio, sr)
            if not transcript:
                await websocket.send_json({"error": "Transcription failed"})
                continue

            llm_result = await ask_llm(transcript, order_id=order_id)
            llm_response = llm_result["text"]
            order_info = llm_result["order"]
            audio_base64 = await speak_text_stream(llm_response)
            os.remove(tmp_path)

            await websocket.send_json({
                "orderId": order_id,
                "user": transcript,
                "transcript": llm_response,
                "response": llm_response,
                "audio": audio_base64,
                "order": order_info
            })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for order_id: {order_id}")


# Serve static files (index.html, JS, CSS)
app.mount("/", StaticFiles(directory=Path(__file__).parent.parent / "public", html=True), name="static")