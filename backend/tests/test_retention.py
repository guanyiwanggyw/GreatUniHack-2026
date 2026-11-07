import math

from app.models import ChudProfile, Note
from app.retention import recompute_knowledge, retention_score


def profile(base=0.2, span=10, weights=None):
    return ChudProfile(
        method_weights=weights or {"DEFINITION": 0.7, "ANALOGY": 0.8, "WORKED_EXAMPLE": 0.9, "DIAGRAM": 0.8, "STEP_BY_STEP": 0.7},
        attention_span=span,
        question_style="fixture",
        persona="fixture",
        base_rate=base,
    )


def note(note_id="n1", turn=1, method="DEFINITION", concept="midpoint", **features):
    merged = {"method": method, "word_count": 6, **features}
    return Note(id=note_id, text=f"{method} note", turn=turn, concept=concept, features=merged)


def test_retention_deterministic():
    notes = [note()]
    first = recompute_knowledge("fixed", notes, 1)
    second = recompute_knowledge("fixed", notes, 1)
    assert first == second


def test_worked_example_scores_above_definition():
    learner = profile(weights={"DEFINITION": 0.4, "ANALOGY": 0.5, "WORKED_EXAMPLE": 0.9, "DIAGRAM": 0.5, "STEP_BY_STEP": 0.5})
    assert retention_score(learner, note(method="WORKED_EXAMPLE"), 1, 1) > retention_score(learner, note(method="DEFINITION"), 1, 1)


def test_reason_bonus_matches_documented_formula():
    learner = profile(base=0.2, weights={"DEFINITION": 0.7, "ANALOGY": 0.7, "WORKED_EXAMPLE": 0.7, "DIAGRAM": 0.7, "STEP_BY_STEP": 0.7})
    scored = retention_score(learner, note(has_reason=True), 1, 1)
    assert math.isclose(scored, 0.2 + 0.55 * 0.7 + 0.08, abs_tol=0.001)


def test_decay_uses_attention_span():
    learner = profile(span=2)
    fresh = retention_score(learner, note(turn=1), 1, 1)
    old = retention_score(learner, note(turn=1), 5, 1)
    assert old < fresh


def test_repetition_recovers_retention():
    learner = profile(span=2)
    old = retention_score(learner, note(turn=1), 5, 1)
    repeated = retention_score(learner, note(turn=1), 5, 3)
    assert repeated > old


def test_score_clamps_to_one():
    learner = profile(base=0.9, weights={"DEFINITION": 1.0, "ANALOGY": 1.0, "WORKED_EXAMPLE": 1.0, "DIAGRAM": 1.0, "STEP_BY_STEP": 1.0})
    assert retention_score(learner, note(has_reason=True, has_example=True), 1, 5) == 1.0


def test_knowledge_has_single_chud_shape():
    knowledge = recompute_knowledge("fixed", [note()], 1)
    assert knowledge.chud_id == "chud"
    assert isinstance(knowledge.retention_scores, dict)
