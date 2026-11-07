from __future__ import annotations

import json
from pathlib import Path

from .config import CONTENT_DIR
from .models import ContentPack, Question


def _pack_dir(pack_id: str) -> Path:
    return CONTENT_DIR / pack_id


def list_packs() -> list[ContentPack]:
    packs: list[ContentPack] = []
    if not CONTENT_DIR.exists():
        return packs
    for path in sorted(CONTENT_DIR.iterdir()):
        if path.is_dir() and (path / "pack.json").exists():
            packs.append(ContentPack.model_validate_json((path / "pack.json").read_text(encoding="utf-8")))
    return packs


def get_pack(pack_id: str) -> ContentPack:
    path = _pack_dir(pack_id) / "pack.json"
    if not path.exists():
        raise KeyError(pack_id)
    return ContentPack.model_validate_json(path.read_text(encoding="utf-8"))


def get_questions(pack_id: str) -> list[Question]:
    path = _pack_dir(pack_id) / "questions.json"
    return [Question.model_validate(item) for item in json.loads(path.read_text(encoding="utf-8"))]


def get_question(pack_id: str, question_id: str | None = None) -> Question:
    questions = get_questions(pack_id)
    if question_id is None:
        return questions[0]
    for question in questions:
        if question.id == question_id:
            return question
    raise KeyError(question_id)


def get_reference(pack_id: str) -> str:
    path = _pack_dir(pack_id) / "reference.md"
    return path.read_text(encoding="utf-8")


def pack_concepts(pack_id: str) -> list[str]:
    concepts: set[str] = set()
    for question in get_questions(pack_id):
        concepts.update(question.concepts)
    return sorted(concepts)


def save_questions(pack_id: str, questions: list[Question]) -> None:
    path = _pack_dir(pack_id) / "questions.json"
    path.write_text(
        json.dumps([q.model_dump() for q in questions], indent=2),
        encoding="utf-8",
    )

