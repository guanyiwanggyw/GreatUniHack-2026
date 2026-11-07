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
    duration_ms: int = 0


def _mock_words(text: str) -> list[dict[str, Any]]:
    words = []
    for index, word in enumerate(text.split()):
        start = index * 0.42
        words.append({"text": word, "start": start, "end": start + 0.28, "type": "word"})
    return words


async def transcribe_audio(filename: str, data: bytes, content_type: str | None = None, keyterms: list[str] | None = None) -> STTResult:
    started = time.perf_counter()
    if mock_mode():
        text = "Binary search checks the middle, then keeps the half that could contain the target."
        result = STTResult(text=text, words=_mock_words(text), duration_ms=4200)
        log_agent_call("stt", int((time.perf_counter() - started) * 1000), len(data), "mock")
        return result

    api_key = env("ELEVENLABS_API_KEY")
    model = env("ELEVENLABS_STT_MODEL", "scribe_v2")
    form: list[tuple[str, str]] = [("model_id", model), ("timestamps_granularity", "word")]
    for term in keyterms or []:
        form.append(("keyterms", term))
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "https://api.elevenlabs.io/v1/speech-to-text",
            headers={"xi-api-key": api_key},
            data=form,
            files={"file": (filename, data, content_type or "application/octet-stream")},
        )
        response.raise_for_status()
        payload = response.json()
    words = payload.get("words", [])
    duration = 0
    if words:
        duration = int(max(float(word.get("end", 0)) for word in words) * 1000)
    log_agent_call("stt", int((time.perf_counter() - started) * 1000), len(data), "ok")
    return STTResult(text=payload.get("text", ""), words=words, duration_ms=duration)


def typed_result(text: str, words: list[dict[str, Any]] | None = None) -> STTResult:
    duration = 0
    if words:
        duration = int(max(float(word.get("end", 0)) for word in words) * 1000)
    return STTResult(text=text, words=words or [], duration_ms=duration)
