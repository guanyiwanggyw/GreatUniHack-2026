from __future__ import annotations

import re
import time
from typing import Any

from pydantic import BaseModel

from ..agent_logging import log_agent_call
from ..models import Note


class ExtractorInput(BaseModel):
    text: str
    turn: int
    pack_concepts: list[str]


class ExtractorOutput(BaseModel):
    notes: list[Note]


CONCEPT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "sorted_precondition": ("sorted", "order first", "ordered list", "any list", "unsorted"),
    "midpoint": ("middle", "midpoint", "centre", "center"),
    "halving": ("half", "halve", "discard", "left side", "right side"),
    "bubble_adjacent_compare": ("bubble", "adjacent", "neighbour", "neighbor"),
    "bubble_swap": ("swap", "out of order"),
    "bubble_passes": ("pass", "largest", "end"),
    "recursion_base_case": ("base case", "stop case"),
    "recursion_self_call": ("calls itself", "recursive call", "recursion"),
    "edge_empty": ("empty", "zero items"),
    "edge_not_found": ("not found", "missing"),
    "termination": ("repeat", "empty", "found", "not found", "stop", "until"),
}


async def run_extractor(payload: ExtractorInput) -> ExtractorOutput:
    started = time.perf_counter()
    chunks = [chunk.strip() for chunk in re.split(r"[.\n;]+", payload.text) if chunk.strip()]
    notes: list[Note] = []
    for index, chunk in enumerate(chunks):
        concept = detect_concept(chunk, payload.pack_concepts)
        if not concept and len(chunks) > 1:
            continue
        words = chunk.split()
        note = Note(
            id=f"t{payload.turn}n{len(notes) + 1}",
            text=chunk,
            turn=payload.turn,
            concept=concept,
            status="pending",
            source="teacher",
            features=features_for(chunk, index + 1),
        )
        notes.append(note)
    if not notes and payload.text.strip():
        notes.append(
            Note(
                id=f"t{payload.turn}n1",
                text=payload.text.strip(),
                turn=payload.turn,
                concept=None,
                status="pending",
                source="teacher",
                features=features_for(payload.text, 1),
            )
        )
    log_agent_call("extractor", int((time.perf_counter() - started) * 1000), len(payload.text), f"{len(notes)} notes")
    return ExtractorOutput(notes=notes)


def detect_concept(text: str, allowed: list[str]) -> str | None:
    lowered = text.lower()
    for concept, keywords in CONCEPT_KEYWORDS.items():
        if concept in allowed and any(keyword in lowered for keyword in keywords):
            return concept
    for concept in allowed:
        if concept.replace("_", " ") in lowered:
            return concept
    return None


def features_for(text: str, step_index: int = 0) -> dict[str, bool | int]:
    lowered = text.lower()
    procedural = any(word in lowered for word in ("first", "then", "next", "after", "repeat", "step", "finally"))
    return {
        "has_reason": any(word in lowered for word in ("because", "so that", "therefore", "why", "means that")),
        "has_example": bool(re.search(r"\d|\[|for example|e\.g\.", lowered)),
        "covers_edge_case": any(word in lowered for word in ("empty", "edge", "boundary", "not found", "fails", "unsorted")),
        "is_procedural_step": procedural,
        "step_index": step_index if procedural else 0,
        "word_count": len(text.split()),
    }

