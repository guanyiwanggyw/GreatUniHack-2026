from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path

from .config import CONTENT_DIR, DEFAULT_PACK_ID
from .models import ContentPack, PastPaper, Question


def _pack_dir(pack_id: str) -> Path:
    return CONTENT_DIR / pack_id


def list_packs() -> list[ContentPack]:
    packs: list[ContentPack] = []
    if not CONTENT_DIR.exists():
        return packs
    for path in sorted(CONTENT_DIR.iterdir()):
        if path.is_dir() and (path / "pack.json").exists():
            packs.append(ContentPack.model_validate_json((path / "pack.json").read_text(encoding="utf-8")))
    # The default pack comes first so clients that take packs[0] start on it.
    packs.sort(key=lambda pack: pack.id != DEFAULT_PACK_ID)
    return packs


def get_pack(pack_id: str) -> ContentPack:
    path = _pack_dir(pack_id) / "pack.json"
    if not path.exists():
        raise KeyError(pack_id)
    return ContentPack.model_validate_json(path.read_text(encoding="utf-8"))


def get_questions(pack_id: str) -> list[Question]:
    path = _pack_dir(pack_id) / "questions.json"
    if not path.exists():
        return []
    return [Question.model_validate(item) for item in json.loads(path.read_text(encoding="utf-8"))]


def get_question(pack_id: str, question_id: str | None = None) -> Question:
    questions = get_questions(pack_id)
    if question_id is not None:
        for question in questions:
            if question.id == question_id:
                return question
        for paper in list_papers(pack_id):
            for question in paper.questions:
                if question.id == question_id:
                    return question
        raise KeyError(question_id)
    if questions:
        return questions[0]
    papers = list_papers(pack_id)
    if papers and papers[0].questions:
        return papers[0].questions[0]
    raise KeyError(f"{pack_id} has no questions")


def get_reference(pack_id: str) -> str:
    path = _pack_dir(pack_id) / "reference.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def pack_concepts(pack_id: str) -> list[str]:
    """Concept ids for a pack: those declared in pack.json plus any used by its questions."""
    concepts: set[str] = set()
    try:
        concepts.update(concept.id for concept in get_pack(pack_id).concepts)
    except KeyError:
        pass
    for question in get_questions(pack_id):
        concepts.update(question.concepts)
    return sorted(concepts)


def concept_names(pack_id: str) -> dict[str, str]:
    try:
        return {concept.id: concept.name for concept in get_pack(pack_id).concepts}
    except KeyError:
        return {}


def concept_keywords(pack_id: str) -> dict[str, list[str]]:
    try:
        return {concept.id: concept.keywords for concept in get_pack(pack_id).concepts}
    except KeyError:
        return {}


def wrong_patterns(pack_id: str) -> list[str]:
    try:
        return get_pack(pack_id).wrong_patterns
    except KeyError:
        return []


def keyword_hits(text: str, keywords: list[str] | tuple[str, ...]) -> int:
    """Count keywords found in text. Purely alphabetic keywords must match whole words, so "tan" does not match "stand"."""
    lowered = text.lower()
    hits = 0
    for keyword in keywords:
        key = keyword.lower()
        if re.fullmatch(r"[a-z ]+", key):
            if re.search(rf"\b{re.escape(key)}\b", lowered):
                hits += 1
        elif key in lowered:
            hits += 1
    return hits


def best_concept(text: str, keywords_by_concept: dict[str, list[str]], allowed: list[str] | None = None) -> str | None:
    best: tuple[int, str] | None = None
    for concept, keywords in keywords_by_concept.items():
        if allowed is not None and concept not in allowed:
            continue
        hits = keyword_hits(text, keywords)
        if hits and (best is None or hits > best[0]):
            best = (hits, concept)
    return best[1] if best else None


def save_questions(pack_id: str, questions: list[Question]) -> None:
    path = _pack_dir(pack_id) / "questions.json"
    path.write_text(
        json.dumps([q.model_dump() for q in questions], indent=2),
        encoding="utf-8",
    )


def _papers_dir(pack_id: str) -> Path:
    return _pack_dir(pack_id) / "papers"


def list_papers(pack_id: str) -> list[PastPaper]:
    folder = _papers_dir(pack_id)
    if not folder.exists():
        return []
    papers = [PastPaper.model_validate_json(path.read_text(encoding="utf-8")) for path in folder.glob("*.json")]
    return sorted(papers, key=lambda paper: paper.created_at, reverse=True)


def get_paper(pack_id: str, paper_id: str) -> PastPaper:
    path = _papers_dir(pack_id) / f"{Path(paper_id).name}.json"
    if not path.exists():
        raise KeyError(paper_id)
    return PastPaper.model_validate_json(path.read_text(encoding="utf-8"))


def save_paper(pack_id: str, title: str, questions: list[Question], source_files: list[str] | None = None, paper_id: str | None = None) -> PastPaper:
    """Store a past paper as its own file. Never touches the pack's practice questions."""
    paper_id = paper_id or f"paper-{uuid.uuid4().hex[:8]}"
    # Question ids are prefixed with the paper id so they stay unique across papers.
    fixed: list[Question] = []
    for index, question in enumerate(questions, start=1):
        q = question.model_copy(deep=True)
        if not q.id.startswith(paper_id):
            q.id = f"{paper_id}-q{index}"
        for point_index, point in enumerate(q.mark_points, start=1):
            point.id = f"{q.id}-m{point_index}"
        q.marks = q.marks or sum(point.marks for point in q.mark_points)
        fixed.append(q)
    paper = PastPaper(
        id=paper_id,
        pack_id=pack_id,
        title=title.strip() or "Untitled past paper",
        questions=fixed,
        total_marks=sum(q.marks for q in fixed),
        source_files=source_files or [],
        created_at=time.time(),
    )
    folder = _papers_dir(pack_id)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{paper.id}.json").write_text(paper.model_dump_json(indent=2), encoding="utf-8")
    return paper


def delete_paper(pack_id: str, paper_id: str) -> None:
    path = _papers_dir(pack_id) / f"{Path(paper_id).name}.json"
    if not path.exists():
        raise KeyError(paper_id)
    path.unlink()
