from __future__ import annotations

import hashlib
import math
import random
from collections import Counter, defaultdict

from .models import ChudKnowledge, ChudProfile, Note
from .profiles import get_profile


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _rng(session_id: str, note_id: str) -> random.Random:
    digest = hashlib.sha256(f"{session_id}:chud:{note_id}".encode()).hexdigest()
    return random.Random(int(digest[:16], 16))


def _feature_value(profile: ChudProfile, note: Note, feature: str) -> float:
    if feature == "short_note":
        return 1.0 if int(note.features.get("word_count", 99)) <= 14 else 0.0
    if feature == "method":
        method = str(note.features.get("method", "DEFINITION"))
        return float(profile.method_weights.get(method, 0.0))
    raw = note.features.get(feature, False)
    if isinstance(raw, bool):
        return 1.0 if raw else 0.0
    if isinstance(raw, (int, float)):
        return float(raw)
    return 0.0


def retention_score(profile: ChudProfile, note: Note, current_turn: int, repeats: int) -> float:
    score = profile.base_rate
    score += 0.55 * _feature_value(profile, note, "method")
    score += 0.08 * _feature_value(profile, note, "has_reason")
    score += 0.08 * _feature_value(profile, note, "has_example")
    score += 0.06 * _feature_value(profile, note, "covers_edge_case")
    score += 0.06 * _feature_value(profile, note, "is_procedural_step")
    decay = math.exp(-max(current_turn - note.turn, 0) / profile.attention_span)
    reinforcement = min(1.0, 0.35 * max(repeats - 1, 0))
    return clamp(score * decay + reinforcement)


def _explanation(profile: ChudProfile, note: Note, score: float, retained: bool) -> str:
    method = str(note.features.get("method", "DEFINITION")).replace("_", " ").lower()
    state = "remembered" if retained else "forgotten"
    if note.status == "incorrect" and retained:
        return f"{profile.name} {state} this {method} note at {round(score * 100)}%, but it contains incorrect teaching."
    if not retained:
        return f"{profile.name} forgot this {method} note as attention decayed to {round(score * 100)}%."
    return f"{profile.name} remembered this {method} note with {round(score * 100)}% retention."


def recompute_knowledge(session_id: str, note_or_ids, notes: list[Note] | int | None = None, current_turn: int | None = None):
    if isinstance(note_or_ids, list) and note_or_ids and isinstance(note_or_ids[0], str):
        actual_notes = notes if isinstance(notes, list) else []
        actual_turn = current_turn if current_turn is not None else 0
        return {"chud": compute_knowledge(session_id, actual_notes, actual_turn)}
    actual_notes = note_or_ids if isinstance(note_or_ids, list) else []
    actual_turn = notes if isinstance(notes, int) else current_turn or 0
    return compute_knowledge(session_id, actual_notes, actual_turn)


def compute_knowledge(session_id: str, notes: list[Note], current_turn: int) -> ChudKnowledge:
    profile = get_profile()
    concept_counts = Counter(note.concept for note in notes if note.concept)
    retained: list[str] = []
    scores: dict[str, float] = {}
    concept_scores: dict[str, list[float]] = defaultdict(list)
    explanations: dict[str, str] = {}
    for note in notes:
        repeats = concept_counts.get(note.concept, 1)
        score = retention_score(profile, note, current_turn, repeats)
        retained_now = _rng(session_id, note.id).random() <= score
        scores[note.id] = round(score, 3)
        if retained_now:
            retained.append(note.id)
        if note.concept:
            concept_scores[note.concept].append(score)
            explanations[note.concept] = _explanation(profile, note, score, retained_now)
    return ChudKnowledge(
        chud_id=profile.id,
        retained_note_ids=retained,
        retention_scores=scores,
        retention_by_concept={concept: round(sum(values) / len(values), 3) for concept, values in concept_scores.items()},
        explanations=explanations,
    )


def retained_notes_for(notes: list[Note], knowledge: ChudKnowledge) -> list[Note]:
    retained = set(knowledge.retained_note_ids)
    return [note for note in notes if note.id in retained]
