# from elevenlabs.client import ElevenLabs
import os
import tempfile
import soundfile as sf
from elevenlabs import ElevenLabs
from dotenv import load_dotenv

load_dotenv()
client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

def transcribe_audio(audio_np, sample_rate):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        sf.write(tmp.name, audio_np, sample_rate)
        tmp_path = tmp.name
    with open(tmp_path, "rb") as f:
        response = client.speech_to_text.convert(file=f, model_id="scribe_v1", language_code="en")
    return response.text.strip() if response and hasattr(response, 'text') else ""
