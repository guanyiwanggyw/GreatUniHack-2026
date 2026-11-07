from __future__ import annotations

import time

from pydantic import BaseModel

from ..agent_logging import log_agent_call
from ..models import Attempt, ChudKnowledge, Note, Question


class CoachInput(BaseModel):
    attempt: Attempt
    question: Question
    transcript: list[dict]
    notes: list[Note]
    knowledge: ChudKnowledge


class CoachOutput(BaseModel):
    gaps: list[dict]
    reteach_suggestions: list[str]
    diagnosis: list[str]


async def run_coach(payload: CoachInput) -> CoachOutput:
    started = time.perf_counter()
    by_mark = {mark.id: mark for mark in payload.question.mark_points}
    remembered = set(payload.knowledge.retained_note_ids)
    gaps = []
    suggestions = []
    diagnosis: list[str] = []
    for mark in payload.attempt.marks:
        if mark.awarded:
            continue
        mark_point = by_mark[mark.mark_point_id]
        concept_notes = [note for note in payload.notes if note.concept == mark_point.concept]
        remembered_notes = [note for note in concept_notes if note.id in remembered]
        if any(note.status == "incorrect" for note in remembered_notes):
            code = "INCORRECT_TEACHING"
            detail = "Chud remembered an incorrect note for this concept."
        elif concept_notes and not remembered_notes:
            code = "DECAY"
            detail = "The concept was taught, but Chud did not remember it."
        elif concept_notes:
            code = "METHOD_MISMATCH"
            detail = "The concept was taught, but not in a way Chud could use in the answer."
        else:
            code = "TEACHING_GAP"
            detail = "The concept was not taught before the test."
        if code not in diagnosis:
            diagnosis.append(code)
        gaps.append({"mark_point_id": mark.mark_point_id, "concept": mark_point.concept, "diagnosis": code, "detail": detail})
        suggestions.append(f"Teach {mark_point.concept} again with a reason, a concrete example, and a short repeat.")
    output = CoachOutput(gaps=gaps, reteach_suggestions=suggestions, diagnosis=diagnosis)
    log_agent_call("coach", int((time.perf_counter() - started) * 1000), len(payload.attempt.answer), "ok")
    return output
