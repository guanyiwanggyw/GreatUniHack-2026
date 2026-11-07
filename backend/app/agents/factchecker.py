from __future__ import annotations

import time
from typing import Literal

from pydantic import BaseModel

from ..agent_logging import log_agent_call
from ..models import MarkPoint, Note


class FactCheckerInput(BaseModel):
    notes: list[Note]
    reference: str
    mark_points: list[MarkPoint]
    # Concepts the pack covers; notes on these count as supported even if the current question does not test them.
    known_concepts: list[str] = []
    # Pack-specific misconceptions, checked alongside the built-in ones.
    wrong_patterns: list[str] = []


class FactCheckItem(BaseModel):
    note_id: str
    status: Literal["correct", "incorrect", "unsupported"]
    reason: str


class FactCheckerOutput(BaseModel):
    checks: list[FactCheckItem]


WRONG_PATTERNS = (
    "binary search works on any list",
    "does not need to be sorted",
    "doesn't need to be sorted",
    "unsorted list is fine",
    "choose a random place instead of the middle",
    "random place instead of the middle",
    "bubble sort is always fastest",
    "does not need adjacent comparisons",
    "doesn't need adjacent comparisons",
    "recursion does not need a base case",
    "recursion never needs a base case",
    "never needs a base case",
    "stops by itself",
)


async def run_factchecker(payload: FactCheckerInput) -> FactCheckerOutput:
    started = time.perf_counter()
    checks: list[FactCheckItem] = []
    known_concepts = {mark.concept for mark in payload.mark_points} | set(payload.known_concepts)
    patterns = (*WRONG_PATTERNS, *(pattern.lower() for pattern in payload.wrong_patterns))
    for note in payload.notes:
        lowered = note.text.lower()
        if any(pattern in lowered for pattern in patterns):
            checks.append(FactCheckItem(note_id=note.id, status="incorrect", reason="Contradicts the reference content."))
        elif note.concept is None or note.concept not in known_concepts:
            checks.append(FactCheckItem(note_id=note.id, status="unsupported", reason="No matching topic in this subject."))
        else:
            checks.append(FactCheckItem(note_id=note.id, status="correct", reason="Matches the reference summary."))
    log_agent_call("factchecker", int((time.perf_counter() - started) * 1000), sum(len(n.text) for n in payload.notes), "ok")
    return FactCheckerOutput(checks=checks)


def apply_checks(notes: list[Note], checks: list[FactCheckItem]) -> list[Note]:
    by_id = {check.note_id: check for check in checks}
    updated: list[Note] = []
    for note in notes:
        if note.id in by_id:
            note.status = by_id[note.id].status
        updated.append(note)
    return updated

