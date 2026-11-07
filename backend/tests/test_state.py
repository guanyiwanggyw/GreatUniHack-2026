from app.models import Session
from app.state import IllegalTransition, transition


def test_legal_transitions():
    session = Session(id="s", pack_id="p", chud_ids=[])
    transition(session, "TEST", "go")
    transition(session, "REVIEW", "graded")
    transition(session, "RETEACH", "missed")
    transition(session, "TEACH", "again")
    assert session.mode == "TEACH"


def test_illegal_transition_raises():
    session = Session(id="s", pack_id="p", chud_ids=[])
    try:
        transition(session, "REVIEW", "bad")
    except IllegalTransition as exc:
        assert "TEST" in exc.allowed
    else:
        raise AssertionError("expected illegal transition")

