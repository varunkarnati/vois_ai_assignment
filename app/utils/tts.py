import json, base64, os, asyncio, websockets, io
import logging
import numpy as np
import soundfile as sf

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = os.getenv("VOICE_ID", "9BWtsMINqrJLrRacOk9x")
MODEL_ID = os.getenv("MODEL_ID", "eleven_turbo_v2")

async def speak_text_stream(text: str) -> str:
    if not ELEVENLABS_API_KEY:
        logger.error("ElevenLabs API key is missing.")
        return ""

    uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream-input?model_id={MODEL_ID}&output_format=pcm_24000"
    logger.info(f"Connecting to ElevenLabs WebSocket: {uri}")

    audio_chunks = b""

    try:
        async with websockets.connect(uri) as websocket:
            await websocket.send(json.dumps({
                "text": " ",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.8
                },
                "xi_api_key": ELEVENLABS_API_KEY,
            }))

            await websocket.send(json.dumps({
                "text": text,
                "try_trigger_generation": True
            }))

            await websocket.send(json.dumps({"text": ""}))

            logger.info("Receiving audio stream...")
            while True:
                try:
                    message_str = await websocket.recv()
                    message = json.loads(message_str)

                    if "audio" in message and message["audio"]:
                        audio_chunks += base64.b64decode(message["audio"])
                    elif message.get("isFinal"):
                        logger.info("Received final message marker.")
                        break
                    elif message.get("error"):
                        logger.error(f"Error from ElevenLabs: {message['error']}")
                        break

                except Exception as e:
                    logger.error(f"WebSocket error: {e}", exc_info=True)
                    break

    except Exception as e:
        logger.error(f"Connection error: {e}", exc_info=True)
        return ""

    if not audio_chunks:
        logger.warning("No audio received from ElevenLabs.")
        return ""

    try:
        audio_np = np.frombuffer(audio_chunks, dtype=np.int16)
        wav_buffer = io.BytesIO()
        sf.write(wav_buffer, audio_np, samplerate=24000, format="WAV")
        wav_buffer.seek(0)
        base64_wav = base64.b64encode(wav_buffer.read()).decode("utf-8")
        logger.info(f"Successfully generated WAV base64, length: {len(base64_wav)}")
        return base64_wav
    except Exception as e:
        logger.error(f"Error converting PCM to WAV: {e}", exc_info=True)
        return ""
