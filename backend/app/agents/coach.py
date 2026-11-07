from __future__ import annotations

import time
from collections import Counter, defaultdict

from pydantic import BaseModel

from ..agent_logging import log_agent_call
from ..models import Attempt, ChudKnowledge, Note, Question


class CoachInput(BaseModel):
    attempts: list[Attempt]
    question: Question
    transcript: list[dict]
    notes: list[Note]
    knowledge: dict[str, ChudKnowledge]


class CoachOutput(BaseModel):
    gaps: list[dict]
    reteach_suggestions: list[str]
    per_chud_breakdown: dict[str, dict]


async def run_coach(payload: CoachInput) -> CoachOutput:
    started = time.perf_counter()
    missed = Counter()
    reasons: dict[str, list[str]] = defaultdict(list)
    for attempt in payload.attempts:
        for mark in attempt.marks:
            if not mark.awarded:
                missed[mark.mark_point_id] += 1
                reasons[mark.mark_point_id].append(f"{attempt.chud_id}: {mark.reason}")
    by_mark = {mark.id: mark for mark in payload.question.mark_points}
    gaps = []
    suggestions = []
    for mark_id, count in missed.most_common():
        mark = by_mark[mark_id]
        supporting_notes = [note for note in payload.notes if note.concept == mark.concept]
        note_detail = "not taught" if not supporting_notes else f"taught {len(supporting_notes)} time(s)"
        gaps.append(
            {
                "mark_point_id": mark_id,
                "concept": mark.concept,
                "missed_by": count,
                "detail": f"{count}/{len(payload.attempts)} chuds missed '{mark.text}'. It was {note_detail}.",
            }
        )
        suggestions.append(f"Re-teach {mark.concept}: {mark.text}. Add a reason, a concrete example, and repeat it once.")
    breakdown = {}
    for attempt in payload.attempts:
        breakdown[attempt.chud_id] = {
            "score": attempt.score,
            "max_score": attempt.max_score,
            "missed": [mark.mark_point_id for mark in attempt.marks if not mark.awarded],
        }
    output = CoachOutput(gaps=gaps, reteach_suggestions=suggestions, per_chud_breakdown=breakdown)
    log_agent_call("coach", int((time.perf_counter() - started) * 1000), len(payload.attempts), "ok")
    return output

