from __future__ import annotations

import asyncio
import os
import time
import uuid

from .agents.chud import ChudInput, ChudTestInput, run_chud, run_test_taker
from .agents.coach import CoachInput, run_coach
from .agents.examiner import KEYWORDS as ALGORITHM_KEYWORDS
from .agents.marker import MarkerInput, run_marker
from .agents.extractor import ExtractorInput, run_extractor
from .agents.factchecker import FactCheckerInput, apply_checks, run_factchecker
from .agents.guardrail import GuardrailInput, run_guardrail
from .agents.output_guard import OutputGuardInput, run_output_guard
from .content import concept_keywords, concept_names, get_paper, get_question, get_reference, pack_concepts, wrong_patterns
from .escalation import maybe_escalate
from .metrics import speech_metrics
from .models import Attempt, BrainConcept, BrainView, PaperAttempt, PaperQuestionResult, PipelineStage, RememberedNote, Session, TeachResponse
from .profiles import get_profile
from .retention import _explanation, recompute_knowledge, retained_notes_for
from .session import save_session
from .state import http_transition
from .stt import STTResult
from .tts import synthesize_speech


PIPELINE_NAMES = [
    "STT",
    "Input guardrail",
    "Extractor",
    "FactChecker",
    "Retention",
    "Chud response",
    "Output guardrail",
    "TTS",
    "Escalation check",
]


class StageTimer:
    def __init__(self, name: str, stages: list[PipelineStage]):
        self.name = name
        self.stages = stages
        self.started = 0.0

    def __enter__(self):
        self.started = time.perf_counter()
        return self

    def done(self, status: str = "ran", detail: str = "") -> None:
        self.stages.append(PipelineStage(name=self.name, status=status, latency_ms=int((time.perf_counter() - self.started) * 1000), detail=detail))

    def __exit__(self, exc_type, exc, tb):
        if exc is None and not any(stage.name == self.name for stage in self.stages):
            self.done()


def _brain_snapshot(session: Session) -> dict:
    view = brain_view(session)
    return {
        "understanding": view.understanding,
        "coverage": {item.concept_id: item.status for item in view.coverage},
        "retained": set(session.knowledge.retained_note_ids),
    }


def _learning_summary(session: Session, before: dict, notes, checks, transcript: str, source: str) -> dict:
    after = _brain_snapshot(session)
    names = concept_names(session.pack_id)
    profile = get_profile(session.chud_id)
    check_by_id = {check.note_id: check for check in checks}
    note_rows = []
    for note in notes:
        score = session.knowledge.retention_scores.get(note.id, 0)
        retained = note.id in after["retained"]
        note_rows.append(
            {
                "id": note.id,
                "text": note.text,
                "concept": note.concept,
                "concept_name": names.get(note.concept or "", (note.concept or "no topic").replace("_", " ")),
                "method": str(note.features.get("method", "DEFINITION")),
                "has_reason": bool(note.features.get("has_reason")),
                "has_example": bool(note.features.get("has_example")),
                "status": note.status,
                "check_reason": check_by_id[note.id].reason if note.id in check_by_id else "",
                "retained": retained,
                "retention": score,
                "memory_reason": _explanation(profile, note, score, retained),
            }
        )
    new_ids = {note.id for note in notes}
    forgotten = [
        {"id": note.id, "text": note.text, "concept_name": names.get(note.concept or "", note.concept or "")}
        for note in session.notes
        if note.id in before["retained"] and note.id not in after["retained"] and note.id not in new_ids
    ]
    changes = [
        {"concept": concept, "name": names.get(concept, concept.replace("_", " ")), "before": before["coverage"].get(concept, "UNTAUGHT"), "after": status}
        for concept, status in after["coverage"].items()
        if before["coverage"].get(concept, "UNTAUGHT") != status
    ]
    return {
        "heard": {"source": source.lower(), "words": len(transcript.split()), "text": transcript},
        "notes": note_rows,
        "forgotten": forgotten,
        "coverage_changes": changes,
        "understanding_before": before["understanding"],
        "understanding_after": after["understanding"],
        "remembered_total": len(after["retained"]),
    }


async def teach_turn(session: Session, stt_result: STTResult, source: str = "TYPED") -> TeachResponse:
    stages: list[PipelineStage] = []
    transcript = stt_result.text.strip()
    before = _brain_snapshot(session)
    with StageTimer("STT", stages) as timer:
        timer.done("ran", source.lower())

    question = get_question(session.pack_id, session.current_question_id)
    with StageTimer("Input guardrail", stages) as timer:
        guard = await run_guardrail(GuardrailInput(text=transcript, mark_points=question.mark_points))
        stage_status = {"allow": "ran", "redirect": "redirected", "block": "blocked"}[guard.verdict]
        timer.done(stage_status, guard.reason)
    if guard.verdict == "block":
        for name in PIPELINE_NAMES[2:]:
            stages.append(PipelineStage(name=name, status="skipped", detail="guardrail blocked"))
        response = _empty_teach_response(session, transcript, stages, stt_result)
        response.reply_reason = guard.reason
        response.learning = {"heard": {"source": source.lower(), "words": len(transcript.split()), "text": transcript}, "stopped": guard.reason, "stopped_by": "block"}
        return response
    if guard.verdict == "redirect":
        reply_text = "Can you say that in your own words?"
        audio_url = await _speak(reply_text)
        session.transcript.append({"role": "chud", "speaker": "Chud", "chud_id": session.chud_id, "text": reply_text, "timestamp": time.time(), "emotion": "CURIOUS"})
        save_session(session)
        for name in PIPELINE_NAMES[2:7]:
            stages.append(PipelineStage(name=name, status="skipped", detail="guardrail redirected"))
        stages.append(PipelineStage(name="TTS", status="ran", detail="redirect reply"))
        stages.append(PipelineStage(name="Escalation check", status="skipped", detail="no committed segment"))
        return TeachResponse(
            transcript=transcript,
            pipeline=stages,
            notes_added=[],
            reply_text=reply_text,
            reply_audio_url=audio_url,
            emotion="CURIOUS",
            knowledge=session.knowledge,
            metrics=speech_metrics(transcript, stt_result.words),
            mode=session.mode,
            reply_reason=guard.reason,
            learning={"heard": {"source": source.lower(), "words": len(transcript.split()), "text": transcript}, "stopped": guard.reason, "stopped_by": "redirect"},
        )

    session.turn += 1
    session.transcript.append({"role": "teacher", "speaker": "Teacher", "text": transcript, "timestamp": time.time(), "source": source})

    with StageTimer("Extractor", stages) as timer:
        extracted = await run_extractor(
            ExtractorInput(text=transcript, turn=session.turn, pack_concepts=pack_concepts(session.pack_id), concept_keywords=concept_keywords(session.pack_id))
        )
        timer.done("ran", f"{len(extracted.notes)} notes")

    with StageTimer("FactChecker", stages) as timer:
        checked = await run_factchecker(
            FactCheckerInput(
                notes=extracted.notes,
                reference=get_reference(session.pack_id),
                mark_points=question.mark_points,
                known_concepts=pack_concepts(session.pack_id),
                wrong_patterns=wrong_patterns(session.pack_id),
            )
        )
        notes = apply_checks(extracted.notes, checked.checks)
        timer.done("ran", f"{len(checked.checks)} checks")

    session.notes.extend(notes)
    with StageTimer("Retention", stages) as timer:
        session.knowledge = recompute_knowledge(session.id, session.notes, session.turn)
        timer.done("ran", "knowledge updated")

    profile = get_profile(session.chud_id)
    retained = retained_notes_for(session.notes, session.knowledge)
    with StageTimer("Chud response", stages) as timer:
        raw = await run_chud(ChudInput(profile=profile, retained_notes=retained, recent_transcript=session.transcript, mode="ask"))
        timer.done("ran", raw.emotion)

    with StageTimer("Output guardrail", stages) as timer:
        guarded = await run_output_guard(OutputGuardInput(text=raw.text, notes=retained))
        timer.done("ran")

    with StageTimer("TTS", stages) as timer:
        audio_url = await _speak(guarded.text)
        session.transcript.append({"role": "chud", "speaker": profile.name, "chud_id": profile.id, "text": guarded.text, "timestamp": time.time(), "emotion": raw.emotion})
        timer.done("ran", "1 clip")

    metrics = speech_metrics(transcript, stt_result.words)
    session.metrics = metrics
    with StageTimer("Escalation check", stages) as timer:
        escalation = maybe_escalate(session)
        timer.done("ran", "escalated" if escalation else "clear")
    save_session(session)
    return TeachResponse(
        transcript=transcript,
        pipeline=stages,
        notes_added=notes,
        reply_text=guarded.text,
        reply_audio_url=audio_url,
        emotion=raw.emotion,
        knowledge=session.knowledge,
        metrics=metrics,
        mode=session.mode,
        reply_reason=raw.reason if guarded.text == raw.text else f"{raw.reason} The output check then reworded it so Chud only says what is in his notes.",
        learning=_learning_summary(session, before, notes, checked.checks, transcript, source),
    )


async def run_test(session: Session, question_id: str | None = None) -> dict:
    if session.mode in ("TEACH", "RETEACH"):
        http_transition(session, "TEST", "teacher_requested_test")
    question = get_question(session.pack_id, question_id or session.current_question_id)
    session.current_question_id = question.id
    session.knowledge = recompute_knowledge(session.id, session.notes, session.turn)
    round_no = max([attempt.round for attempt in session.attempts if attempt.question_id == question.id], default=0) + 1
    profile = get_profile(session.chud_id)
    retained = retained_notes_for(session.notes, session.knowledge)
    answer = await run_test_taker(ChudTestInput(profile=profile, question=question, retained_notes=retained))
    marked = await run_marker(_marker_input(session.pack_id, question, answer.answer))
    attempt = Attempt(
        id=str(uuid.uuid4()),
        question_id=question.id,
        chud_id=session.chud_id,
        answer=answer.answer,
        marks=marked.marks,
        score=marked.score,
        max_score=marked.max_score,
        round=round_no,
    )
    session.attempts.append(attempt)
    if session.mode == "TEST":
        http_transition(session, "REVIEW", "attempt_graded")
    coach = await run_coach(CoachInput(attempt=attempt, question=question, transcript=session.transcript, notes=session.notes, knowledge=session.knowledge))
    summary = {"round": round_no, "average": attempt.score, "max_score": attempt.max_score, "full_marks": attempt.score == attempt.max_score, "marker": marked.marker}
    session.feedback.append({**coach.model_dump(), "question_id": question.id, "class_summary": summary})
    maybe_escalate(session)
    save_session(session)
    return {"question": question, "attempt": attempt, "class_summary": summary}


def _marker_input(pack_id: str, question, answer: str) -> MarkerInput:
    keywords = concept_keywords(pack_id) or {concept: list(words) for concept, words in ALGORITHM_KEYWORDS.items()}
    return MarkerInput(question=question, answer=answer, concept_keywords=keywords, wrong_patterns=wrong_patterns(pack_id))


async def sit_paper(session: Session, paper_id: str) -> PaperAttempt:
    """Chud answers every question on a past paper from its remembered notes; the Marker marks each against the mark scheme."""
    paper = get_paper(session.pack_id, paper_id)
    if session.mode in ("TEACH", "RETEACH"):
        http_transition(session, "TEST", "teacher_requested_paper")
    session.knowledge = recompute_knowledge(session.id, session.notes, session.turn)
    profile = get_profile(session.chud_id)
    retained = retained_notes_for(session.notes, session.knowledge)
    limit = asyncio.Semaphore(4)

    async def answer_and_mark(question):
        async with limit:
            answer = await run_test_taker(ChudTestInput(profile=profile, question=question, retained_notes=retained))
            marked = await run_marker(_marker_input(session.pack_id, question, answer.answer))
        result = PaperQuestionResult(
            question_id=question.id,
            question_text=question.text,
            answer=answer.answer,
            marks=marked.marks,
            score=marked.score,
            max_score=marked.max_score,
        )
        return result, marked.marker

    outcomes = await asyncio.gather(*(answer_and_mark(question) for question in paper.questions))
    results = [result for result, _ in outcomes]
    score = sum(result.score for result in results)
    max_score = sum(result.max_score for result in results) or 1
    percentage = round(100 * score / max_score, 1)
    attempt = PaperAttempt(
        id=str(uuid.uuid4()),
        paper_id=paper.id,
        paper_title=paper.title,
        results=results,
        score=score,
        max_score=max_score,
        percentage=percentage,
        marker="llm" if any(marker == "llm" for _, marker in outcomes) else "heuristic",
        summary=_paper_summary(session.pack_id, paper, results, score, max_score, percentage),
        created_at=time.time(),
    )
    session.paper_attempts.append(attempt)
    if session.mode == "TEST":
        http_transition(session, "REVIEW", "paper_marked")
    save_session(session)
    return attempt


def _paper_summary(pack_id: str, paper, results: list[PaperQuestionResult], score: int, max_score: int, percentage: float) -> str:
    names = concept_names(pack_id)
    gained: dict[str, int] = {}
    available: dict[str, int] = {}
    by_question = {question.id: question for question in paper.questions}
    for result in results:
        points = {point.id: point for point in by_question[result.question_id].mark_points}
        for mark in result.marks:
            point = points.get(mark.mark_point_id)
            if not point:
                continue
            available[point.concept] = available.get(point.concept, 0) + point.marks
            if mark.awarded:
                gained[point.concept] = gained.get(point.concept, 0) + point.marks
    ratios = {concept: gained.get(concept, 0) / total for concept, total in available.items() if total}
    label = lambda concept: names.get(concept, concept.replace("_", " "))  # noqa: E731
    strong = [label(c) for c, r in sorted(ratios.items(), key=lambda item: -item[1]) if r >= 0.75][:3]
    weak = [label(c) for c, r in sorted(ratios.items(), key=lambda item: item[1]) if r < 0.5][:3]
    parts = [f"Chud scored {score}/{max_score} ({percentage:g}%)."]
    if strong:
        parts.append(f"Strongest: {', '.join(strong)}.")
    if weak:
        parts.append(f"Teach next: {', '.join(weak)}.")
    return " ".join(parts)


async def review(session: Session) -> dict:
    if not session.feedback:
        question = get_question(session.pack_id, session.current_question_id)
        attempt = next((item for item in reversed(session.attempts) if item.question_id == question.id), None)
        if attempt is None:
            return {"gaps": [], "reteach_suggestions": [], "diagnosis": []}
        coach = await run_coach(CoachInput(attempt=attempt, question=question, transcript=session.transcript, notes=session.notes, knowledge=session.knowledge))
        session.feedback.append({**coach.model_dump(), "question_id": question.id})
        save_session(session)
    return session.feedback[-1]


def begin_reteach(session: Session) -> dict:
    if session.mode == "REVIEW":
        http_transition(session, "RETEACH", "teacher_reteach")
    if session.mode == "RETEACH":
        http_transition(session, "TEACH", "reteach_ready")
    save_session(session)
    return {"mode": session.mode, "prompt": "Teach the missed idea again with a reason, a concrete example, and one repeat."}


async def recap(session: Session) -> dict:
    profile = get_profile(session.chud_id)
    retained = retained_notes_for(session.notes, session.knowledge)
    reply = await run_chud(ChudInput(profile=profile, retained_notes=retained, recent_transcript=session.transcript, mode="recap"))
    audio_url = await _speak(reply.text)
    session.transcript.append({"role": "chud", "speaker": profile.name, "chud_id": profile.id, "text": reply.text, "timestamp": time.time(), "emotion": reply.emotion, "mode": "recap"})
    save_session(session)
    return {"reply_text": reply.text, "reply_audio_url": audio_url, "emotion": reply.emotion}


def brain_view(session: Session) -> BrainView:
    profile = get_profile(session.chud_id)
    retained = set(session.knowledge.retained_note_ids)
    remembered = [
        RememberedNote(
            note=note,
            retained=note.id in retained,
            retention=session.knowledge.retention_scores.get(note.id, 0),
            reason=session.knowledge.explanations.get(note.concept or "", "No concept-specific retention reason."),
        )
        for note in session.notes
    ]
    concepts = pack_concepts(session.pack_id)
    names = concept_names(session.pack_id)
    coverage = []
    for concept in concepts:
        concept_notes = [note for note in session.notes if note.concept == concept]
        remembered_notes = [note for note in concept_notes if note.id in retained]
        if not concept_notes:
            status = "UNTAUGHT"
        elif not any(note.status == "correct" for note in remembered_notes) or any(note.status == "incorrect" for note in remembered_notes):
            status = "SHAKY"
        else:
            status = "SOLID"
        coverage.append(BrainConcept(concept_id=concept, name=names.get(concept, concept.replace("_", " ")), status=status))
    solid = sum(1 for item in coverage if item.status == "SOLID")
    last = session.attempts[-1] if session.attempts else None
    paper = session.paper_attempts[-1] if session.paper_attempts else None
    last_paper = (
        {"paper_id": paper.paper_id, "title": paper.paper_title, "score": paper.score, "max": paper.max_score, "percentage": paper.percentage}
        if paper
        else None
    )
    return BrainView(
        chud=profile,
        notes=remembered,
        coverage=coverage,
        understanding=round(solid / max(len(coverage), 1), 3),
        last_score={"score": last.score, "max": last.max_score} if last else None,
        last_paper=last_paper,
        show_correctness=bool(session.feedback or session.paper_attempts),
    )


async def _speak(text: str) -> str:
    profile = get_profile()
    voice_id = os.getenv("ELEVENLABS_VOICE_CHUD", profile.voice_id)
    return await synthesize_speech(text, voice_id, profile.id)


def _empty_teach_response(session: Session, transcript: str, stages: list[PipelineStage], stt_result: STTResult) -> TeachResponse:
    return TeachResponse(
        transcript=transcript,
        pipeline=stages,
        notes_added=[],
        reply_text="",
        reply_audio_url="",
        emotion="NEUTRAL",
        knowledge=session.knowledge,
        metrics=speech_metrics(transcript, stt_result.words),
        mode=session.mode,
    )
