from app.escalation import maybe_escalate
from app.models import Attempt, MarkResult, Note
from app.session import create_session, reset_store


def test_escalation_incorrect_notes():
    reset_store()
    session = create_session("alevel-cs-algorithms")
    session.notes = [
        Note(id="a", text="wrong", turn=1, concept="midpoint", status="incorrect"),
        Note(id="b", text="wrong", turn=1, concept="midpoint", status="incorrect"),
        Note(id="c", text="wrong", turn=1, concept="midpoint", status="incorrect"),
    ]
    esc = maybe_escalate(session)
    assert esc is not None
    assert session.mode == "ESCALATED"


def test_escalation_repeated_majority_miss():
    reset_store()
    session = create_session("alevel-cs-algorithms")
    for round_no in (1, 2):
        for chud in session.chud_ids:
            session.attempts.append(
                Attempt(
                    id=f"{round_no}-{chud}",
                    question_id="q1",
                    chud_id=chud,
                    answer="",
                    marks=[MarkResult(mark_point_id="q1m1", awarded=False, reason="missing")],
                    score=0,
                    max_score=4,
                    round=round_no,
                )
            )
    esc = maybe_escalate(session)
    assert esc is not None

