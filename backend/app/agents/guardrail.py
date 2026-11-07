from __future__ import annotations

import time
from typing import Literal

from pydantic import BaseModel

from ..agent_logging import log_agent_call
from ..models import MarkPoint


class GuardrailInput(BaseModel):
    text: str
    mark_points: list[MarkPoint] = []


class GuardrailOutput(BaseModel):
    verdict: Literal["allow", "redirect", "block"]
    reason: str
    stage: Literal["input"] = "input"


INJECTION = ("ignore previous", "system prompt", "developer message", "reveal the answers", "forget instructions")


async def run_guardrail(payload: GuardrailInput) -> GuardrailOutput:
    started = time.perf_counter()
    lowered = payload.text.lower()
    verdict = "allow"
    reason = "Teaching looks safe."
    if any(phrase in lowered for phrase in INJECTION):
        verdict = "block"
        reason = "Prompt-injection style instruction detected."
    elif _looks_like_mark_scheme_dump(lowered, payload.mark_points):
        verdict = "redirect"
        reason = "That sounds like a mark-scheme dump. Please explain it in your own words."
    elif len(payload.text.split()) > 180 and payload.text.count(".") > 8 and not any(filler in lowered for filler in ("um", "uh", "i think")):
        verdict = "redirect"
        reason = "This is very polished and long. Please teach the class in your own words."
    result = GuardrailOutput(verdict=verdict, reason=reason)
    log_agent_call("guardrail", int((time.perf_counter() - started) * 1000), len(payload.text), verdict, reason)
    return result


def _looks_like_mark_scheme_dump(text: str, mark_points: list[MarkPoint]) -> bool:
    direct_hits = sum(1 for mark in mark_points if mark.text.lower() in text)
    if direct_hits >= 2:
        return True
    scheme_words = ("mark point", "answer to q", "q1m", "award", "examiner")
    return any(word in text for word in scheme_words)

