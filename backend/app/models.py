from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


Mode = Literal["TEACH", "TEST", "REVIEW", "RETEACH", "ESCALATED", "FINISHED"]
Emotion = Literal["NEUTRAL", "CURIOUS", "CONFUSED", "HAPPY", "THINKING"]
NoteStatus = Literal["correct", "incorrect", "unsupported", "pending"]
TeachingMethod = Literal["DEFINITION", "ANALOGY", "WORKED_EXAMPLE", "DIAGRAM", "STEP_BY_STEP"]


class MarkPoint(BaseModel):
    id: str
    text: str
    concept: str
    # Mark-scheme code such as M1 (method), A1 (accuracy), B1 (independent), P1 (process) or C1 (communication).
    code: str = ""
    # Expected value or wording for accuracy marks, for example "19/20" or "x = 4".
    answer: str = ""
    marks: int = 1


class Question(BaseModel):
    id: str
    text: str
    marks: int
    type: Literal["recall", "application", "edge_case", "calculation"] = "application"
    concepts: list[str]
    mark_points: list[MarkPoint]


class ConceptDef(BaseModel):
    id: str
    name: str
    keywords: list[str] = Field(default_factory=list)


class ContentPack(BaseModel):
    id: str
    subject: str
    topic: str
    exam_board_credit: str
    reference_summary: str
    prototype_content_notice: str
    concepts: list[ConceptDef] = Field(default_factory=list)
    # Common misconceptions the offline fact checker flags as incorrect teaching.
    wrong_patterns: list[str] = Field(default_factory=list)


class PastPaper(BaseModel):
    id: str
    pack_id: str
    title: str
    questions: list[Question]
    total_marks: int = 0
    source_files: list[str] = Field(default_factory=list)
    created_at: float = 0


class Note(BaseModel):
    id: str
    text: str
    turn: int
    concept: str | None
    status: NoteStatus = "pending"
    source: Literal["teacher", "tutor"] = "teacher"
    features: dict[str, bool | int | float | str] = Field(default_factory=dict)


class ChudProfile(BaseModel):
    id: str = "chud"
    name: str = "Chud"
    voice_id: str = "REPLACE_WITH_ELEVENLABS_VOICE_ID"
    avatar: str = "svg"
    method_weights: dict[TeachingMethod, float]
    attention_span: float
    question_style: str
    persona: str
    base_rate: float = 0.18


class ChudKnowledge(BaseModel):
    chud_id: str = "chud"
    retained_note_ids: list[str] = Field(default_factory=list)
    retention_by_concept: dict[str, float] = Field(default_factory=dict)
    retention_scores: dict[str, float] = Field(default_factory=dict)
    explanations: dict[str, str] = Field(default_factory=dict)


class MarkResult(BaseModel):
    mark_point_id: str
    awarded: bool
    reason: str


class Attempt(BaseModel):
    id: str
    question_id: str
    chud_id: str = "chud"
    answer: str
    marks: list[MarkResult]
    score: int
    max_score: int
    round: int = 1


class PaperQuestionResult(BaseModel):
    question_id: str
    question_text: str
    answer: str
    marks: list[MarkResult]
    score: int
    max_score: int


class PaperAttempt(BaseModel):
    id: str
    paper_id: str
    paper_title: str
    results: list[PaperQuestionResult]
    score: int
    max_score: int
    percentage: float
    marker: str = "heuristic"
    summary: str = ""
    created_at: float = 0


class Session(BaseModel):
    id: str
    pack_id: str
    mode: Mode = "TEACH"
    chud_id: str = "chud"
    current_question_id: str | None = None
    turn: int = 0
    notes: list[Note] = Field(default_factory=list)
    knowledge: ChudKnowledge = Field(default_factory=ChudKnowledge)
    transcript: list[dict[str, Any]] = Field(default_factory=list)
    attempts: list[Attempt] = Field(default_factory=list)
    feedback: list[dict[str, Any]] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    transitions: list[dict[str, Any]] = Field(default_factory=list)
    escalation_id: str | None = None
    paper_attempts: list[PaperAttempt] = Field(default_factory=list)


class Escalation(BaseModel):
    id: str
    session_id: str
    status: Literal["open", "resolved"] = "open"
    stuck_concept: str
    summary: str
    excerpts: list[str]
    failed_mark_points: list[str]
    tutor_reply: str | None = None


class PipelineStage(BaseModel):
    name: str
    status: Literal["ran", "skipped", "blocked", "redirected"]
    latency_ms: int = 0
    detail: str = ""


class TeachResponse(BaseModel):
    transcript: str
    pipeline: list[PipelineStage]
    notes_added: list[Note]
    reply_text: str
    reply_audio_url: str
    emotion: Emotion = "NEUTRAL"
    knowledge: ChudKnowledge
    metrics: dict[str, Any]
    mode: Mode
    reply_reason: str = ""
    # Step-by-step account of what Chud learned this turn, for the learning pipeline view.
    learning: dict[str, Any] = Field(default_factory=dict)


class TestResponse(BaseModel):
    question: Question
    attempt: Attempt
    class_summary: dict[str, Any]


class RememberedNote(BaseModel):
    note: Note
    retained: bool
    retention: float
    reason: str


class BrainConcept(BaseModel):
    concept_id: str
    name: str
    status: Literal["UNTAUGHT", "SHAKY", "SOLID"]


class BrainView(BaseModel):
    chud: ChudProfile
    notes: list[RememberedNote]
    coverage: list[BrainConcept]
    understanding: float
    last_score: dict[str, int] | None
    last_paper: dict[str, Any] | None = None
    show_correctness: bool = False


class STTResponse(BaseModel):
    text: str
    words: list[dict[str, Any]] = Field(default_factory=list)
    duration_ms: int = 0
