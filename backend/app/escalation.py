from __future__ import annotations

import uuid
from collections import Counter, defaultdict

from .models import Escalation, Note, Session
from .session import add_escalation
from .state import transition


def _repeated_single_miss(session: Session) -> list[str]:
    by_question: dict[str, dict[int, set[str]]] = defaultdict(lambda: defaultdict(set))
    for attempt in session.attempts:
        for mark in attempt.marks:
            if not mark.awarded:
                by_question[attempt.question_id][attempt.round].add(mark.mark_point_id)
    repeated: list[str] = []
    for rounds in by_question.values():
        ordered = sorted(rounds)
        for first, second in zip(ordered, ordered[1:]):
            repeated.extend(sorted(rounds[first] & rounds[second]))
    return sorted(set(repeated))


def maybe_escalate(session: Session) -> Escalation | None:
    if session.mode == "ESCALATED":
        return None
    incorrect_notes = [note for note in session.notes if note.status == "incorrect"]
    failed = _repeated_single_miss(session)
    if len(incorrect_notes) < 3 and not failed:
        return None
    concept_counts = Counter(note.concept or "unknown" for note in incorrect_notes)
    stuck = concept_counts.most_common(1)[0][0] if concept_counts else failed[0]
    excerpts = [line["text"] for line in session.transcript if line.get("role") == "teacher"][-4:]
    escalation = Escalation(
        id=str(uuid.uuid4()),
        session_id=session.id,
        stuck_concept=stuck,
        summary=f"Chud is stuck on {stuck}. Incorrect notes: {len(incorrect_notes)}. Repeated missed marks: {', '.join(failed) or 'none'}.",
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
            "method": "DEFINITION",
        },
    )
