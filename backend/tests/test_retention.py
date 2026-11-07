from app.models import Note
from app.profiles import get_profile
from app.retention import recompute_knowledge, retention_score


def test_retention_deterministic():
    notes = [Note(id="n1", text="sorted because halves only work with order", turn=1, concept="sorted_precondition", features={"has_reason": True, "word_count": 7})]
    first = recompute_knowledge("s", ["sam"], notes, 1)
    second = recompute_knowledge("s", ["sam"], notes, 1)
    assert first == second


def test_sam_prefers_reason():
    sam = get_profile("sam")
    with_reason = Note(id="a", text="sorted because order lets us discard half", turn=1, concept="sorted_precondition", features={"has_reason": True, "word_count": 7})
    without_reason = Note(id="b", text="the list is sorted", turn=1, concept="sorted_precondition", features={"has_reason": False, "word_count": 4})
    assert retention_score(sam, with_reason, 1, 1) > retention_score(sam, without_reason, 1, 1)


def test_ollie_decays_and_repetition_recovers():
    ollie = get_profile("ollie")
    note = Note(id="n", text="check the middle", turn=1, concept="midpoint", features={"word_count": 3})
    old = retention_score(ollie, note, 8, 1)
    repeated = retention_score(ollie, note, 8, 3)
    assert old < retention_score(ollie, note, 1, 1)
    assert repeated > old

