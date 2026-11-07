from __future__ import annotations

import re
import time

from pydantic import BaseModel

from ..agent_logging import log_agent_call
from ..models import Note


class OutputGuardInput(BaseModel):
    text: str
    notes: list[Note]


class OutputGuardOutput(BaseModel):
    ok: bool
    leaked_claims: list[str] = []
    text: str


async def run_output_guard(payload: OutputGuardInput) -> OutputGuardOutput:
    started = time.perf_counter()
    leaked: list[str] = []
    supported = " ".join(note.text.lower() for note in payload.notes)
    sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", payload.text) if sentence.strip()]
    kept: list[str] = []
    for sentence in sentences:
        lowered = sentence.lower()
        content_words = [word.strip(".,!?") for word in lowered.split() if len(word) > 5]
        if content_words and supported and not any(word in supported for word in content_words[:4]) and "don't know" not in lowered:
            leaked.append(sentence)
        else:
            kept.append(sentence)
    result_text = " ".join(kept) if leaked else payload.text
    if not result_text:
        result_text = "I don't know from my notes yet."
    result = OutputGuardOutput(ok=not leaked, leaked_claims=leaked, text=result_text)
    outcome = "leakage" if leaked else "ok"
    log_agent_call("output_guard", int((time.perf_counter() - started) * 1000), len(payload.text), outcome)
    return result

