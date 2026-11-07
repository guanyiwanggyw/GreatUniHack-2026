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


def test_escalation_repeated_mark_missed_two_rounds():
    reset_store()
    session = create_session("alevel-cs-algorithms")
    qid = session.current_question_id or "q"
    for round_no in (1, 2):
        session.attempts.append(
            Attempt(
                id=f"{round_no}-chud",
                question_id=qid,
                answer="",
                marks=[MarkResult(mark_point_id="m1", awarded=False, reason="missing")],
                score=0,
                max_score=4,
                round=round_no,
            )
        )
    esc = maybe_escalate(session)
    assert esc is not None
