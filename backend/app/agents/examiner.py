from __future__ import annotations

import time

from pydantic import BaseModel

from ..agent_logging import log_agent_call
from ..models import MarkResult, Question


class ExaminerInput(BaseModel):
    question: Question
    answer: str


class ExaminerOutput(BaseModel):
    marks: list[MarkResult]
    total_score: int


KEYWORDS: dict[str, tuple[str, ...]] = {
    "sorted_precondition": ("sorted", "ordered"),
    "midpoint": ("middle", "midpoint", "centre", "center"),
    "halving": ("half", "discard", "halve"),
    "termination": ("repeat", "until", "empty", "found", "stop"),
    "bubble_adjacent_compare": ("adjacent", "neighbour", "neighbor", "compare"),
    "bubble_swap": ("swap", "out of order"),
    "bubble_passes": ("pass", "largest", "end"),
    "recursion_base_case": ("base case", "stopping case"),
    "recursion_self_call": ("calls itself", "recursive call"),
    "edge_empty": ("empty", "zero"),
    "edge_not_found": ("not found", "missing"),
}

NEGATIONS: dict[str, tuple[str, ...]] = {
    "sorted_precondition": ("any list", "does not need to be sorted", "doesn't need to be sorted", "unsorted list is fine"),
    "midpoint": ("random place", "instead of the middle", "not the middle"),
    "halving": ("keep both halves", "do not discard", "don't discard"),
    "termination": ("forever", "never stops", "does not stop"),
    "bubble_adjacent_compare": ("does not need adjacent", "doesn't need adjacent"),
    "bubble_swap": ("does not swap", "doesn't swap"),
    "recursion_base_case": ("never needs a base case", "does not need a base case", "doesn't need a base case"),
    "termination": ("forever", "never stops", "does not stop", "stops by itself", "never needs a base case"),
}


async def run_examiner(payload: ExaminerInput) -> ExaminerOutput:
    started = time.perf_counter()
    lowered = payload.answer.lower()
    marks: list[MarkResult] = []
    for mark_point in payload.question.mark_points:
        awarded = _awards(mark_point.concept, lowered)
        marks.append(
            MarkResult(
                mark_point_id=mark_point.id,
                awarded=awarded,
                reason="Present in the answer." if awarded else f"Missing: {mark_point.text}",
            )
        )
    total = sum(1 for mark in marks if mark.awarded)
    log_agent_call("examiner", int((time.perf_counter() - started) * 1000), len(payload.answer), f"{total}/{payload.question.marks}")
    return ExaminerOutput(marks=marks, total_score=total)


def _awards(concept: str, answer: str) -> bool:
    if any(phrase in answer for phrase in NEGATIONS.get(concept, ())):
        return False
    return any(keyword in answer for keyword in KEYWORDS.get(concept, (concept.replace("_", " "),)))

