from __future__ import annotations

import time

from pydantic import BaseModel

from ..agent_logging import log_agent_call
from ..models import ChudProfile, Note, Question


class ChudInput(BaseModel):
    profile: ChudProfile
    retained_notes: list[Note]
    recent_transcript: list[dict]


class ChudOutput(BaseModel):
    chud_id: str
    text: str
    question: str | None = None


class ChudTestInput(BaseModel):
    profile: ChudProfile
    question: Question
    retained_notes: list[Note]


class ChudTestOutput(BaseModel):
    chud_id: str
    answer: str


def build_chud_prompt(profile: ChudProfile, retained_notes: list[Note], recent_transcript: list[dict] | None = None) -> str:
    note_lines = "\n".join(f"- {note.text}" for note in retained_notes) or "- No retained notes."
    transcript_lines = "\n".join(line.get("text", "") for line in (recent_transcript or [])[-4:])
    return (
        "You are a student who just left school. You know ONLY the notes below. "
        "If something isn't in the notes, say you don't know or guess badly. Never use outside knowledge.\n\n"
        f"Student: {profile.name} ({profile.description})\n"
        f"Questioning style: {profile.questioning_style}\n\n"
        f"RETAINED NOTES:\n{note_lines}\n\nRECENT TRANSCRIPT:\n{transcript_lines}"
    )


async def run_chud(payload: ChudInput) -> ChudOutput:
    started = time.perf_counter()
    text = _reply_text(payload.profile, payload.retained_notes)
    output = ChudOutput(chud_id=payload.profile.id, text=text, question=text if "?" in text else None)
    log_agent_call("chud", int((time.perf_counter() - started) * 1000), len(build_chud_prompt(payload.profile, payload.retained_notes)), "ok")
    return output


async def run_test_taker(payload: ChudTestInput) -> ChudTestOutput:
    started = time.perf_counter()
    relevant = [note for note in payload.retained_notes if note.concept in payload.question.concepts]
    if not relevant:
        answer = "I don't really know from my notes."
    else:
        answer = " ".join(note.text for note in relevant[:5])
        if any(note.status == "incorrect" for note in relevant):
            answer += " I am confident about that because it was in my notes."
    log_agent_call("chud_test_taker", int((time.perf_counter() - started) * 1000), len(answer), "ok")
    return ChudTestOutput(chud_id=payload.profile.id, answer=answer)


def _reply_text(profile: ChudProfile, notes: list[Note]) -> str:
    if not notes:
        return f"I don't know enough yet. {profile.questioning_style}"
    newest = notes[-1]
    if profile.id == "sam" and not newest.features.get("has_reason"):
        return "I heard the rule, but why does that work?"
    if profile.id == "priya" and not newest.features.get("covers_edge_case"):
        return "What happens in the edge case, like an empty list or when it is not found?"
    if profile.id == "leo" and not newest.features.get("has_example"):
        return "I sort of get it, but can you show me with numbers?"
    if profile.id == "mia" and not newest.features.get("is_procedural_step"):
        return "What comes after that step? I need the order."
    if profile.id == "ollie":
        return "Can you repeat the important bit once more?"
    return f"Okay, I think I retained: {newest.text[:120]}."

