from __future__ import annotations

import uuid
from collections import Counter, defaultdict

from .models import Escalation, Note, Session
from .session import add_escalation
from .state import transition


def _majority_missed_by_round(session: Session) -> list[str]:
    by_round: dict[int, dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))
    for attempt in session.attempts:
        for mark in attempt.marks:
            by_round[attempt.round][mark.mark_point_id].append(mark.awarded)
    missed_majority: list[str] = []
    rounds = sorted(by_round)
    if len(rounds) < 2:
        return []
    last_two = rounds[-2:]
    for mark_point in by_round[last_two[0]]:
        first = by_round[last_two[0]][mark_point]
        second = by_round[last_two[1]].get(mark_point, [])
        if first and second and sum(not item for item in first) > len(first) / 2 and sum(not item for item in second) > len(second) / 2:
            missed_majority.append(mark_point)
    return missed_majority


def maybe_escalate(session: Session) -> Escalation | None:
    if session.mode == "ESCALATED":
        return None
    incorrect_notes = [note for note in session.notes if note.status == "incorrect"]
    failed = _majority_missed_by_round(session)
    if len(incorrect_notes) < 3 and not failed:
        return None
    concept_counts = Counter(note.concept or "unknown" for note in incorrect_notes)
    stuck = concept_counts.most_common(1)[0][0] if concept_counts else failed[0]
    excerpts = [line["text"] for line in session.transcript if line.get("role") == "teacher"][-4:]
    escalation = Escalation(
        id=str(uuid.uuid4()),
        session_id=session.id,
        stuck_concept=stuck,
        summary=f"Class is stuck on {stuck}. Incorrect notes: {len(incorrect_notes)}. Repeated missed marks: {', '.join(failed) or 'none'}.",
        excerpts=excerpts,
        failed_mark_points=failed,
    )
    add_escalation(escalation)
    session.escalation_id = escalation.id
    transition(session, "ESCALATED", "escalation_rule")
    return escalation


def tutor_note_from_reply(session: Session, hint: str) -> Note:
    concept = "tutor_hint"
    for note in session.notes:
        if note.concept and note.concept in hint.lower().replace(" ", "_"):
            concept = note.concept
            break
    return Note(
        id=f"tutor-{len(session.notes) + 1}",
        text=hint,
        turn=session.turn + 1,
        concept=concept,
        status="correct",
        source="tutor",
        features={
            "has_reason": "because" in hint.lower(),
            "has_example": any(char.isdigit() for char in hint),
            "covers_edge_case": "empty" in hint.lower() or "edge" in hint.lower(),
            "is_procedural_step": "then" in hint.lower() or "step" in hint.lower(),
            "step_index": 0,
            "word_count": len(hint.split()),
        },
    )

