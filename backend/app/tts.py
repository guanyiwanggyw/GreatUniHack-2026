from __future__ import annotations

import hashlib
import time

import httpx

from .agent_logging import log_agent_call
from .config import AUDIO_DIR, env, voice_available

MOCK_MP3 = b"ID3\x04\x00\x00\x00\x00\x00\x15Teach-Chud mock audio"


async def synthesize_speech(text: str, voice_id: str | None, chud_id: str) -> str:
    started = time.perf_counter()
    digest = hashlib.sha1(f"{chud_id}:{text}".encode()).hexdigest()[:16]
    filename = f"{chud_id}-{digest}.mp3"
    path = AUDIO_DIR / filename
    if not voice_available():
        path.write_bytes(MOCK_MP3)
        log_agent_call("tts", int((time.perf_counter() - started) * 1000), len(text), "mock")
        return f"/api/audio/{filename}"

    api_key = env("ELEVENLABS_API_KEY")
    model = env("ELEVENLABS_TTS_MODEL", "eleven_flash_v2_5")
    output_format = env("ELEVENLABS_OUTPUT_FORMAT", "mp3_44100_128")
    resolved_voice = voice_id or env("ELEVENLABS_VOICE_CHUD", "JBFqnCBsd6RMkjVDRZzb")
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{resolved_voice}",
            params={"output_format": output_format},
            headers={"xi-api-key": api_key, "Content-Type": "application/json"},
            json={"text": text, "model_id": model},
        )
        response.raise_for_status()
        path.write_bytes(response.content)
    log_agent_call("tts", int((time.perf_counter() - started) * 1000), len(text), "ok")
    return f"/api/audio/{filename}"

