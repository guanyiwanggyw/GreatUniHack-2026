from __future__ import annotations

import time

from pydantic import BaseModel

from ..agent_logging import log_agent_call
from ..models import ChudProfile, Emotion, Note, Question


class ChudInput(BaseModel):
    profile: ChudProfile
    retained_notes: list[Note]
    recent_transcript: list[dict]
    mode: str = "ask"


class ChudOutput(BaseModel):
    text: str
    emotion: Emotion = "NEUTRAL"


class ChudTestInput(BaseModel):
    profile: ChudProfile
    question: Question
    retained_notes: list[Note]


class ChudTestOutput(BaseModel):
    chud_id: str = "chud"
    answer: str


def build_chud_prompt(profile: ChudProfile, retained_notes: list[Note], recent_transcript: list[dict] | None = None, mode: str = "ask") -> str:
    note_lines = "\n".join(f"- {note.text}" for note in retained_notes) or "- No remembered notes."
    transcript_lines = "\n".join(line.get("text", "") for line in (recent_transcript or [])[-4:])
    return (
        "You are Chud, one student beside a whiteboard. You know ONLY the remembered notes below. "
        "If something is not in those notes, say you are unsure. Never use outside knowledge.\n\n"
        f"Persona: {profile.persona}\n"
        f"Question style: {profile.question_style}\n"
        f"Mode: {mode}\n\n"
        f"REMEMBERED NOTES:\n{note_lines}\n\nRECENT TRANSCRIPT:\n{transcript_lines}"
    )


async def run_chud(payload: ChudInput) -> ChudOutput:
    started = time.perf_counter()
    if payload.mode == "recap":
        output = _recap(payload.retained_notes)
    else:
        output = _ask(payload.retained_notes)
    log_agent_call("chud", int((time.perf_counter() - started) * 1000), len(build_chud_prompt(payload.profile, payload.retained_notes, payload.recent_transcript, payload.mode)), "ok")
    return output


async def run_test_taker(payload: ChudTestInput) -> ChudTestOutput:
    started = time.perf_counter()
    relevant = [note for note in payload.retained_notes if note.concept in payload.question.concepts]
    if not relevant:
        answer = "I do not really know from my notes."
    else:
        answer = " ".join(note.text for note in relevant[:6])
        if any(note.status == "incorrect" for note in relevant):
            answer += " I am confident because it is in my remembered notes."
    log_agent_call("chud_test_taker", int((time.perf_counter() - started) * 1000), len(answer), "ok")
    return ChudTestOutput(answer=answer)


def _ask(notes: list[Note]) -> ChudOutput:
    if not notes:
        return ChudOutput(text="I am not sure yet. Can you give me an example?", emotion="CURIOUS")
    newest = notes[-1]
    if newest.status == "incorrect":
        return ChudOutput(text="Wait, that feels muddled in my notes. Can you explain why?", emotion="CONFUSED")
    if not newest.features.get("has_reason"):
        return ChudOutput(text="I heard that bit, but wait, why does it work?", emotion="CURIOUS")
    if not newest.features.get("has_example") and newest.features.get("method") != "WORKED_EXAMPLE":
        return ChudOutput(text="I think I get the idea. Could you show me one example?", emotion="CURIOUS")
    return ChudOutput(text=f"That clicked: {newest.text[:120]}.", emotion="HAPPY")


def _recap(notes: list[Note]) -> ChudOutput:
    if not notes:
        return ChudOutput(text="I do not have any remembered notes yet. I am unsure about the whole topic.", emotion="CONFUSED")
    correct = [note for note in notes if note.status != "incorrect"]
    if not correct:
        return ChudOutput(text="I only remember notes that might be wrong, so I am not confident. I need you to reteach the basics.", emotion="CONFUSED")
    parts = [note.text for note in correct[:4]]
    unsure = [note.concept for note in notes if note.status in ("unsupported", "incorrect") and note.concept]
    tail = " I am unsure about " + ", ".join(sorted(set(unsure))) + "." if unsure else " I am not sure what comes next unless you test me."
    return ChudOutput(text="Here is what I think I know: " + " ".join(parts) + tail, emotion="THINKING")
