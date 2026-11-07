from __future__ import annotations

import time
from typing import Any

import httpx
from pydantic import BaseModel, Field

from .agent_logging import log_agent_call
from .config import env, mock_mode


class STTResult(BaseModel):
    text: str
    words: list[dict[str, Any]] = Field(default_factory=list)


def _mock_words(text: str) -> list[dict[str, Any]]:
    words = []
    for index, word in enumerate(text.split()):
        start = index * 0.42
        words.append({"text": word, "start": start, "end": start + 0.28, "type": "word"})
    return words


async def transcribe_audio(filename: str, data: bytes, content_type: str | None = None) -> STTResult:
    started = time.perf_counter()
    if mock_mode():
        text = "Binary search checks the middle, then keeps the half that could contain the target."
        result = STTResult(text=text, words=_mock_words(text))
        log_agent_call("stt", int((time.perf_counter() - started) * 1000), len(data), "mock")
        return result

    api_key = env("ELEVENLABS_API_KEY")
    model = env("ELEVENLABS_STT_MODEL", "scribe_v2")
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "https://api.elevenlabs.io/v1/speech-to-text",
            headers={"xi-api-key": api_key},
            data={"model_id": model},
            files={"file": (filename, data, content_type or "application/octet-stream")},
        )
        response.raise_for_status()
        payload = response.json()
    log_agent_call("stt", int((time.perf_counter() - started) * 1000), len(data), "ok")
    return STTResult(text=payload.get("text", ""), words=payload.get("words", []))


def typed_result(text: str) -> STTResult:
    return STTResult(text=text, words=[])

