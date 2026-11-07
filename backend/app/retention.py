from __future__ import annotations

import hashlib
import math
import random
from collections import Counter, defaultdict

from .models import ChudKnowledge, ChudProfile, Note
from .profiles import get_profile


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _rng(session_id: str, chud_id: str, note_id: str) -> random.Random:
    digest = hashlib.sha256(f"{session_id}:{chud_id}:{note_id}".encode()).hexdigest()
    return random.Random(int(digest[:16], 16))


def _feature_value(note: Note, feature: str) -> float:
    if feature == "short_note":
        return 1.0 if int(note.features.get("word_count", 99)) <= 14 else 0.0
    raw = note.features.get(feature, False)
    if isinstance(raw, bool):
        return 1.0 if raw else 0.0
    if isinstance(raw, int):
        return float(raw)
    return 0.0


def retention_score(profile: ChudProfile, note: Note, current_turn: int, repeats: int) -> float:
    score = profile.base_rate
    for feature, weight in profile.weights.items():
        score += weight * _feature_value(note, feature)
    decay = math.exp(-max(current_turn - note.turn, 0) / profile.memory_span)
    reinforcement = min(1.0, 0.35 * max(repeats - 1, 0))
    return clamp(score * decay + reinforcement)


def _explanation(profile: ChudProfile, note: Note, score: float) -> str:
    needs = profile.description.lower()
    if profile.id == "sam" and not note.features.get("has_reason"):
        return f"{profile.name}: retained {round(score * 100)}% because {needs} and this was stated without a reason."
    if profile.id == "leo" and not note.features.get("has_example"):
        return f"{profile.name}: retained {round(score * 100)}% because {needs} and no worked example was given."
    if profile.id == "priya" and not note.features.get("covers_edge_case"):
        return f"{profile.name}: retained {round(score * 100)}% because {needs} and no edge case was covered."
    if profile.id == "mia" and not note.features.get("is_procedural_step"):
        return f"{profile.name}: retained {round(score * 100)}% because {needs} and this was not clearly ordered."
    if profile.id == "ollie":
        return f"{profile.name}: retained {round(score * 100)}% because short-attention retention depends on recency and repetition."
    return f"{profile.name}: retained {round(score * 100)}%."


def recompute_knowledge(session_id: str, chud_ids: list[str], notes: list[Note], current_turn: int) -> dict[str, ChudKnowledge]:
    concept_counts = Counter(note.concept for note in notes if note.concept)
    knowledge: dict[str, ChudKnowledge] = {}
    for chud_id in chud_ids:
        profile = get_profile(chud_id)
        retained: list[str] = []
        scores: dict[str, float] = {}
        concept_scores: dict[str, list[float]] = defaultdict(list)
        explanations: dict[str, str] = {}
        for note in notes:
            repeats = concept_counts.get(note.concept, 1)
            score = retention_score(profile, note, current_turn, repeats)
            scores[note.id] = round(score, 3)
            if note.concept:
                concept_scores[note.concept].append(score)
                explanations[note.concept] = _explanation(profile, note, score)
            if _rng(session_id, chud_id, note.id).random() <= score:
                retained.append(note.id)
        knowledge[chud_id] = ChudKnowledge(
            chud_id=chud_id,
            retained_note_ids=retained,
            retention_scores=scores,
            retention_by_concept={concept: round(sum(values) / len(values), 3) for concept, values in concept_scores.items()},
            explanations=explanations,
        )
    return knowledge


def retained_notes_for(chud_id: str, notes: list[Note], knowledge: dict[str, ChudKnowledge]) -> list[Note]:
    retained = set(knowledge.get(chud_id, ChudKnowledge(chud_id=chud_id)).retained_note_ids)
    return [note for note in notes if note.id in retained]

