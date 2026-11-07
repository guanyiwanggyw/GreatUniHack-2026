from __future__ import annotations

import json
import re
import time
from pathlib import Path

from pydantic import BaseModel

from ..agent_logging import log_agent_call
from ..content import keyword_hits
from ..llm import LLMUnavailable, llm
from ..models import MarkPoint, MarkResult, Question

PROMPT = (Path(__file__).resolve().parents[1] / "prompts" / "marker.md").read_text(encoding="utf-8")

NO_ANSWER = ("i do not really know", "i don't know", "i do not know", "not sure")

SCHEMA = {
    "type": "object",
    "properties": {
        "marks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "mark_point_id": {"type": "string"},
                    "awarded": {"type": "boolean"},
                    "reason": {"type": "string"},
                },
                "required": ["mark_point_id", "awarded", "reason"],
            },
        }
    },
    "required": ["marks"],
}


class MarkerInput(BaseModel):
    question: Question
    answer: str
    concept_keywords: dict[str, list[str]] = {}
    wrong_patterns: list[str] = []


class MarkerOutput(BaseModel):
    marks: list[MarkResult]
    score: int
    max_score: int
    marker: str = "heuristic"


async def run_marker(payload: MarkerInput) -> MarkerOutput:
    """Mark one answer against its mark scheme. Uses the LLM when configured, otherwise the offline rules."""
    started = time.perf_counter()
    marks: list[MarkResult] | None = None
    marker = "heuristic"
    try:
        marks = await _llm_marks(payload)
        marker = "llm"
    except LLMUnavailable:
        pass
    except Exception as error:  # noqa: BLE001 - any LLM failure falls back to offline marking
        log_agent_call("marker", int((time.perf_counter() - started) * 1000), len(payload.answer), "llm_error", str(error)[:200])
    if marks is None:
        marks = _heuristic_marks(payload)
    by_id = {point.id: point for point in payload.question.mark_points}
    score = sum(by_id[mark.mark_point_id].marks for mark in marks if mark.awarded and mark.mark_point_id in by_id)
    max_score = max(payload.question.marks, sum(point.marks for point in payload.question.mark_points))
    log_agent_call("marker", int((time.perf_counter() - started) * 1000), len(payload.answer), f"{score}/{max_score} {marker}")
    return MarkerOutput(marks=marks, score=min(score, max_score), max_score=max_score, marker=marker)


async def _llm_marks(payload: MarkerInput) -> list[MarkResult]:
    scheme = [
        {"mark_point_id": p.id, "code": p.code, "marks": p.marks, "mark_scheme": p.text, "expected_answer": p.answer}
        for p in payload.question.mark_points
    ]
    user = (
        f"QUESTION ({payload.question.marks} marks):\n{payload.question.text}\n\n"
        f"MARK SCHEME:\n{json.dumps(scheme, ensure_ascii=False, indent=1)}\n\n"
        f"<answer>\n{payload.answer}\n</answer>"
    )
    result = await llm(PROMPT, [{"role": "user", "content": user}], json_schema=SCHEMA, agent="marker_llm")
    assert isinstance(result, dict)
    returned = {item["mark_point_id"]: item for item in result.get("marks", []) if isinstance(item, dict) and "mark_point_id" in item}
    marks: list[MarkResult] = []
    for point in payload.question.mark_points:
        item = returned.get(point.id)
        if item is None:
            marks.append(MarkResult(mark_point_id=point.id, awarded=False, reason="Marker gave no decision for this point."))
        else:
            marks.append(MarkResult(mark_point_id=point.id, awarded=bool(item.get("awarded")), reason=str(item.get("reason", ""))[:300]))
    return marks


def normalise(text: str) -> str:
    text = text.lower()
    for old, new in (("−", "-"), ("–", "-"), ("×", "x"), ("÷", "/"), ("£", ""), ("$", ""), ("²", "^2"), ("³", "^3"), ("°", "")):
        text = text.replace(old, new)
    return re.sub(r"\s+", "", text)


def answer_present(expected: str, answer: str) -> bool:
    """True when every part of the expected answer appears in the answer as a whole value, so "10" does not match "100"."""
    parts = [part for part in re.split(r"\s+and\s+|,|;|\bor\b", expected.lower()) if part.strip()]
    if not parts:
        return False
    target = normalise(answer)
    for part in parts:
        value = normalise(re.sub(r"\b(cm|mm|m|km|kg|g|cm\^2|cm\^3|degrees|oe|cao|ft)\b", "", part))
        if not value:
            continue
        pattern = rf"(?<![\d./]){re.escape(value)}(?![\d/]|\.\d)"
        if not re.search(pattern, target):
            return False
    return True


def _heuristic_marks(payload: MarkerInput) -> list[MarkResult]:
    answer = payload.answer.lower()
    gave_up = not answer.strip() or any(phrase in answer for phrase in NO_ANSWER) and len(answer.split()) < 12
    misconception = next((pattern for pattern in payload.wrong_patterns if pattern.lower() in answer), None)
    points = payload.question.mark_points
    results: list[MarkResult] = []
    for point in points:
        results.append(_mark_point(point, payload, answer, gave_up, misconception))
    # A correct final answer implies the method marks before it.
    for index, (point, result) in enumerate(zip(points, results)):
        if point.code.upper().startswith("A") and result.awarded:
            for earlier in range(index):
                if points[earlier].code.upper().startswith(("M", "P")) and not results[earlier].awarded:
                    results[earlier] = MarkResult(mark_point_id=points[earlier].id, awarded=True, reason="Implied by the correct final answer.")
    return results


def _mark_point(point: MarkPoint, payload: MarkerInput, answer: str, gave_up: bool, misconception: str | None) -> MarkResult:
    if gave_up:
        return MarkResult(mark_point_id=point.id, awarded=False, reason="Chud did not attempt an answer.")
    if point.answer:
        if answer_present(point.answer, payload.answer):
            return MarkResult(mark_point_id=point.id, awarded=True, reason=f"Correct answer {point.answer} given.")
        return MarkResult(mark_point_id=point.id, awarded=False, reason=f"Expected {point.answer}.")
    if misconception:
        return MarkResult(mark_point_id=point.id, awarded=False, reason=f"Method contradicted by the misconception \"{misconception}\".")
    keywords = payload.concept_keywords.get(point.concept) or [point.concept.replace("_", " ")]
    scheme_numbers = re.findall(r"\d+(?:\.\d+)?(?:/\d+)?", point.text)
    if scheme_numbers and answer_present(scheme_numbers[-1], payload.answer):
        return MarkResult(mark_point_id=point.id, awarded=True, reason="Working matches the mark scheme values.")
    if keyword_hits(answer, keywords):
        return MarkResult(mark_point_id=point.id, awarded=True, reason=f"Uses a correct {point.concept.replace('_', ' ')} method.")
    return MarkResult(mark_point_id=point.id, awarded=False, reason=f"Missing: {point.text}")
