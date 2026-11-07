from __future__ import annotations

import json
import re
import time
from pathlib import Path

from pydantic import BaseModel, Field

from ..agent_logging import log_agent_call
from ..content import best_concept, concept_keywords, keyword_hits, pack_concepts
from ..llm import LLMUnavailable, llm
from ..models import MarkPoint, Question

PROMPT = (Path(__file__).resolve().parents[1] / "prompts" / "paper_ingest.md").read_text(encoding="utf-8")
MAX_LLM_CHARS = 60_000


class PaperIngestInput(BaseModel):
    paper_text: str
    mark_scheme_text: str
    pack_id: str
    paper_filename: str = ""


class PaperIngestOutput(BaseModel):
    draft_questions: list[Question]
    title: str = ""
    total_marks: int = 0
    extractor: str = "heuristic"
    warnings: list[str] = Field(default_factory=list)


async def run_paper_ingest(payload: PaperIngestInput) -> PaperIngestOutput:
    started = time.perf_counter()
    size = len(payload.paper_text) + len(payload.mark_scheme_text)
    warnings: list[str] = []
    if len(payload.paper_text.strip()) < 40:
        warnings.append("Almost no text could be read from the paper PDF. It may be a scanned image; try a PDF with selectable text.")
    if len(payload.mark_scheme_text.strip()) < 40:
        warnings.append("Almost no text could be read from the mark scheme PDF. Marks will need to be added by hand.")

    output: PaperIngestOutput | None = None
    try:
        output = await _llm_ingest(payload)
    except LLMUnavailable:
        pass
    except Exception as error:  # noqa: BLE001 - fall back to the offline parser
        warnings.append("The AI extractor failed, so the offline parser was used instead.")
        log_agent_call("paper_ingest", int((time.perf_counter() - started) * 1000), size, "llm_error", str(error)[:200])
    if output is None or not output.draft_questions:
        output = heuristic_ingest(payload)
    output.warnings = warnings + output.warnings
    output.title = output.title or _guess_title(payload.paper_text, payload.paper_filename)
    output.total_marks = sum(question.marks for question in output.draft_questions)
    log_agent_call("paper_ingest", int((time.perf_counter() - started) * 1000), size, f"{len(output.draft_questions)} questions {output.extractor}")
    return output


# ---------- AI extraction ----------

def _schema(allowed: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "number": {"type": "string"},
                        "text": {"type": "string"},
                        "marks": {"type": "integer"},
                        "concepts": {"type": "array", "items": {"type": "string", "enum": allowed}},
                        "mark_points": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "code": {"type": "string"},
                                    "marks": {"type": "integer"},
                                    "text": {"type": "string"},
                                    "answer": {"type": "string"},
                                    "concept": {"type": "string", "enum": allowed},
                                },
                                "required": ["code", "marks", "text", "answer", "concept"],
                            },
                        },
                    },
                    "required": ["number", "text", "marks", "concepts", "mark_points"],
                },
            },
        },
        "required": ["title", "questions"],
    }


async def _llm_ingest(payload: PaperIngestInput) -> PaperIngestOutput:
    allowed = pack_concepts(payload.pack_id) or ["general"]
    user = (
        f"ALLOWED CONCEPT IDS: {', '.join(allowed)}\n\n"
        f"<paper>\n{payload.paper_text[:MAX_LLM_CHARS]}\n</paper>\n\n"
        f"<mark_scheme>\n{payload.mark_scheme_text[:MAX_LLM_CHARS]}\n</mark_scheme>"
    )
    result = await llm(PROMPT, [{"role": "user", "content": user}], json_schema=_schema(allowed), timeout=180, agent="paper_ingest_llm")
    assert isinstance(result, dict)
    questions: list[Question] = []
    for index, item in enumerate(result.get("questions", []), start=1):
        concepts = [c for c in item.get("concepts", []) if c in allowed] or [allowed[0]]
        points = []
        for point_index, point in enumerate(item.get("mark_points", []), start=1):
            concept = point.get("concept") if point.get("concept") in allowed else concepts[0]
            points.append(
                MarkPoint(
                    id=f"draft-{index}-m{point_index}",
                    code=str(point.get("code", ""))[:4],
                    marks=max(int(point.get("marks", 1) or 1), 1),
                    text=str(point.get("text", "")),
                    answer=str(point.get("answer", "")),
                    concept=concept,
                )
            )
        marks = int(item.get("marks") or 0) or sum(p.marks for p in points)
        questions.append(
            Question(
                id=f"draft-{index}",
                text=f"{item.get('number', index)}. {item.get('text', '').strip()}",
                marks=marks,
                type="calculation" if re.search(r"\d", item.get("text", "")) else "application",
                concepts=concepts,
                mark_points=points or [_full_credit_point(index, marks, concepts[0])],
            )
        )
    return PaperIngestOutput(draft_questions=questions, title=str(result.get("title", "")), extractor="llm")


# ---------- Offline parser ----------

NOISE = re.compile(
    r"do not write in this area|turn over|leave blank|^\*?p\d{4,}|^page \d+|©|pearson|edexcel|aqa|ocr|wjec|"
    r"^blank page|^\(total for paper|^total for paper|^question number|^answer\s+mark|^mark scheme|^paper code",
    re.I,
)
TOTAL_FOR = re.compile(r"\(?\s*total\s+for\s+question\s+(\d+)\s+is\s+(\d+)\s+marks?\s*\)?", re.I)
PART_MARKS = re.compile(r"(?:\[\s*(\d+)\s*(?:marks?)?\s*\]|\(\s*(\d+)\s*\))\s*$", re.I)
# Question number, optional part such as "(a)" or "a" (but not "x = 7"), then the rest of the line.
QUESTION_LINE = re.compile(r"^\s*(\d{1,2})\s*(\(\s*[a-z]{1,3}\s*\)|[a-h](?=\s|$)(?!\s*[=+\-*/^]))?[\s.)]*(.*)$", re.I)
ANSWER_LABEL = re.compile(r"^(?:[a-z]\s*=|cm|mm|m|km|kg|g|£|degrees|°)$", re.I)
CODE = re.compile(r"\b([MABPC])(\d)\b")
ALTERNATIVE = re.compile(r"\(\s*[MABPC]\d\b[^)]*\)")


def _clean_lines(text: str) -> list[str]:
    lines = []
    for raw in text.replace("\r", "\n").split("\n"):
        line = re.sub(r"\.{4,}|_{4,}", " ", raw).strip()
        if line and not NOISE.search(line) and not re.fullmatch(r"\d{1,3}", line) and not ANSWER_LABEL.match(line):
            lines.append(line)
    return lines


def _segments(lines: list[str], allow_same_number: bool) -> dict[int, list[str]]:
    """Split lines into numbered questions. A question starts only at the next expected number, which skips stray numbers in the text."""
    segments: dict[int, list[str]] = {}
    current = 0
    for line in lines:
        match = QUESTION_LINE.match(line)
        if match:
            number = int(match.group(1))
            rest = (match.group(3) or "").strip()
            starts_question = number == current + 1 and (rest or match.group(2))
            # Avoid treating "3 cm" or "2 x" inside a question as a new question.
            if starts_question and not allow_same_number and re.match(r"^(cm|mm|m|kg|g|km|x|y|n)\b", rest, re.I) and not match.group(2):
                starts_question = False
            if starts_question:
                current = number
                segments[current] = [line]
                continue
            if allow_same_number and number == current and match.group(2):
                segments.setdefault(current, []).append(line)
                continue
        if current:
            segments.setdefault(current, []).append(line)
    return segments


def _question_text_and_marks(lines: list[str]) -> tuple[str, int]:
    joined = "\n".join(lines)
    total = TOTAL_FOR.search(joined)
    marks = int(total.group(2)) if total else 0
    if not marks:
        marks = sum(int(m.group(1) or m.group(2)) for line in lines for m in [PART_MARKS.search(line)] if m)
    text = TOTAL_FOR.sub("", joined)
    text = re.sub(r"[ \t]+", " ", text).strip()
    return text[:1500], marks


def _answer_column(line: str) -> str:
    match = QUESTION_LINE.match(line)
    body = (match.group(3) if match else line) or ""
    first_code = CODE.search(body)
    return (body[: first_code.start()] if first_code else "").strip(" |:-")


def _scheme_points(lines: list[str], q_index: int, concept: str, keywords: dict[str, list[str]]) -> list[MarkPoint]:
    points: list[MarkPoint] = []
    answer_column = ""
    for line in lines:
        line = ALTERNATIVE.sub("", line)
        column = _answer_column(line)
        if column and len(column) < 40:
            answer_column = column
        codes = list(CODE.finditer(line))
        for i, code in enumerate(codes):
            end = codes[i + 1].start() if i + 1 < len(codes) else len(line)
            description = line[code.end(): end].strip(" ,;:|-")
            letter, weight = code.group(1), int(code.group(2))
            answer = ""
            value = re.sub(r"\b(oe|cao|ft|or equivalent)\b", "", description, flags=re.I).strip()
            if letter in "AB":
                if value.lower().startswith("for "):
                    candidate = value[4:].strip()
                    answer = candidate if len(candidate) < 25 and re.search(r"\d", candidate) else ""
                elif not value or len(value) < 25 and re.search(r"\d", value):
                    answer = value or answer_column
            text = description or (f"Correct answer {answer_column}" if answer_column else f"{letter}{weight} mark")
            point_concept = best_concept(f"{text} {line}", keywords) or concept
            points.append(
                MarkPoint(
                    id=f"draft-{q_index}-m{len(points) + 1}",
                    code=f"{letter}{weight}",
                    marks=weight,
                    text=text[:300],
                    answer=answer[:60],
                    concept=point_concept,
                )
            )
    return points


def _full_credit_point(index: int, marks: int, concept: str) -> MarkPoint:
    return MarkPoint(id=f"draft-{index}-m1", code=f"B{max(marks, 1)}", marks=max(marks, 1), text="Full credit as per the mark scheme. Edit this point.", answer="", concept=concept)


def heuristic_ingest(payload: PaperIngestInput) -> PaperIngestOutput:
    keywords = concept_keywords(payload.pack_id)
    allowed = pack_concepts(payload.pack_id) or ["general"]
    paper = _segments(_clean_lines(payload.paper_text), allow_same_number=False)
    scheme = _segments(_clean_lines(payload.mark_scheme_text), allow_same_number=True)
    warnings: list[str] = []
    numbers = sorted(set(paper) | set(scheme))
    questions: list[Question] = []
    for index, number in enumerate(numbers, start=1):
        text, marks = _question_text_and_marks(paper.get(number, [f"{number} (question text not found in the paper)"]))
        scheme_text = " ".join(scheme.get(number, []))
        ranked = sorted(allowed, key=lambda c: -keyword_hits(f"{text} {scheme_text}", keywords.get(c, [c.replace("_", " ")])))
        main = best_concept(text, keywords) or best_concept(scheme_text, keywords) or ranked[0]
        extra = [c for c in ranked if c != main and keyword_hits(text, keywords.get(c, [])) > 0][:2]
        points = _scheme_points(scheme.get(number, []), index, main, keywords)
        scheme_marks = sum(point.marks for point in points)
        if not marks:
            marks = scheme_marks
        if not points:
            points = [_full_credit_point(index, marks, main)]
            warnings.append(f"Question {number}: no mark codes found in the mark scheme. Check its marks.")
        elif marks and scheme_marks != marks:
            warnings.append(f"Question {number}: the paper says {marks} marks but the mark scheme points add to {scheme_marks}.")
        questions.append(
            Question(
                id=f"draft-{index}",
                text=text,
                marks=marks or 1,
                type="calculation" if re.search(r"\d", text[3:]) else "application",
                concepts=[main, *extra],
                mark_points=points,
            )
        )
    if not questions:
        warnings.append("No numbered questions were found. Check the PDFs contain selectable text.")
    return PaperIngestOutput(draft_questions=questions, extractor="heuristic", warnings=warnings)


def _guess_title(text: str, filename: str) -> str:
    for line in text.splitlines()[:25]:
        clean = line.strip()
        if 8 < len(clean) < 90 and re.search(r"paper|gcse|mathematics|maths", clean, re.I) and not NOISE.search(clean):
            return clean
    return Path(filename).stem.replace("_", " ").replace("-", " ").strip() or "Uploaded past paper"
