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


class Question(BaseModel):
    id: str
    text: str
    marks: int
    type: Literal["recall", "application", "edge_case"]
    concepts: list[str]
    mark_points: list[MarkPoint]


class ContentPack(BaseModel):
    id: str
    subject: str
    topic: str
    exam_board_credit: str
    reference_summary: str
    prototype_content_notice: str


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
    show_correctness: bool = False


class STTResponse(BaseModel):
    text: str
    words: list[dict[str, Any]] = Field(default_factory=list)
    duration_ms: int = 0
