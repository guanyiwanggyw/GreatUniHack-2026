from __future__ import annotations

import asyncio
import os
import time
import uuid

from .agents.chud import ChudInput, ChudTestInput, run_chud, run_test_taker
from .agents.coach import CoachInput, run_coach
from .agents.examiner import ExaminerInput, run_examiner
from .agents.extractor import ExtractorInput, run_extractor
from .agents.factchecker import FactCheckerInput, apply_checks, run_factchecker
from .agents.guardrail import GuardrailInput, run_guardrail
from .agents.output_guard import OutputGuardInput, run_output_guard
from .content import get_question, get_questions, get_reference, pack_concepts
from .escalation import maybe_escalate
from .metrics import speech_metrics
from .models import Attempt, PipelineStage, Session, TeachResponse
from .profiles import get_profile
from .retention import recompute_knowledge, retained_notes_for
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


async def teach_turn(session: Session, stt_result: STTResult) -> TeachResponse:
    stages: list[PipelineStage] = []
    transcript = stt_result.text.strip()
    with StageTimer("STT", stages) as timer:
        timer.done("ran", "typed input" if not stt_result.words else "audio transcribed")

    question = get_question(session.pack_id, session.current_question_id)
    with StageTimer("Input guardrail", stages) as timer:
        guard = await run_guardrail(GuardrailInput(text=transcript, mark_points=question.mark_points))
        stage_status = {"allow": "ran", "redirect": "redirected", "block": "blocked"}[guard.verdict]
        timer.done(stage_status, guard.reason)
    if guard.verdict == "block":
        for name in PIPELINE_NAMES[2:]:
            stages.append(PipelineStage(name=name, status="skipped", detail="guardrail blocked"))
        return TeachResponse(
            transcript=transcript,
            pipeline=stages,
            notes_added=[],
            replies=[],
            knowledge=session.knowledge,
            metrics=speech_metrics(transcript, stt_result.words),
            mode=session.mode,
        )
    if guard.verdict == "redirect":
        session.transcript.append({"role": "system", "speaker": "guardrail", "text": guard.reason, "timestamp": time.time()})
        save_session(session)
        for name in PIPELINE_NAMES[2:]:
            stages.append(PipelineStage(name=name, status="skipped", detail="guardrail redirected"))
        return TeachResponse(
            transcript=transcript,
            pipeline=stages,
            notes_added=[],
            replies=[{"chud_id": "system", "text": guard.reason, "audio_url": ""}],
            knowledge=session.knowledge,
            metrics=speech_metrics(transcript, stt_result.words),
            mode=session.mode,
        )

    session.turn += 1
    session.transcript.append({"role": "teacher", "speaker": "Teacher", "text": transcript, "timestamp": time.time()})

    with StageTimer("Extractor", stages) as timer:
        extracted = await run_extractor(ExtractorInput(text=transcript, turn=session.turn, pack_concepts=pack_concepts(session.pack_id)))
        timer.done("ran", f"{len(extracted.notes)} notes")

    with StageTimer("FactChecker", stages) as timer:
        checked = await run_factchecker(
            FactCheckerInput(notes=extracted.notes, reference=get_reference(session.pack_id), mark_points=question.mark_points)
        )
        notes = apply_checks(extracted.notes, checked.checks)
        timer.done("ran", f"{len(checked.checks)} checks")

    session.notes.extend(notes)
    with StageTimer("Retention", stages) as timer:
        session.knowledge = recompute_knowledge(session.id, session.chud_ids, session.notes, session.turn)
        timer.done("ran", "knowledge updated")

    selected = _select_chuds(session, notes)
    raw_replies = []
    with StageTimer("Chud response", stages) as timer:
        for chud_id in selected:
            profile = get_profile(chud_id)
            retained = retained_notes_for(chud_id, session.notes, session.knowledge)
            raw_replies.append(await run_chud(ChudInput(profile=profile, retained_notes=retained, recent_transcript=session.transcript)))
        timer.done("ran", ",".join(selected))

    guarded_replies = []
    with StageTimer("Output guardrail", stages) as timer:
        for reply in raw_replies:
            retained = retained_notes_for(reply.chud_id, session.notes, session.knowledge)
            guarded = await run_output_guard(OutputGuardInput(text=reply.text, notes=retained))
            guarded_replies.append({"chud_id": reply.chud_id, "text": guarded.text})
        timer.done("ran")

    replies = []
    with StageTimer("TTS", stages) as timer:
        for reply in guarded_replies:
            profile = get_profile(reply["chud_id"])
            audio_url = await synthesize_speech(reply["text"], os.getenv(profile.voice_id_env), reply["chud_id"])
            replies.append({**reply, "audio_url": audio_url})
            session.transcript.append({"role": "chud", "speaker": profile.name, "chud_id": profile.id, "text": reply["text"], "timestamp": time.time()})
        timer.done("ran", f"{len(replies)} clips")

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
        replies=replies,
        knowledge=session.knowledge,
        metrics=metrics,
        mode=session.mode,
    )


async def run_test(session: Session, question_id: str | None = None) -> dict:
    if session.mode not in ("TEACH", "RETEACH", "REVIEW"):
        pass
    if session.mode in ("TEACH", "RETEACH"):
        http_transition(session, "TEST", "teacher_requested_test")
    question = get_question(session.pack_id, question_id or session.current_question_id)
    session.current_question_id = question.id
    session.knowledge = recompute_knowledge(session.id, session.chud_ids, session.notes, session.turn)
    round_no = max([attempt.round for attempt in session.attempts if attempt.question_id == question.id], default=0) + 1

    async def attempt_for(chud_id: str) -> Attempt:
        profile = get_profile(chud_id)
        retained = retained_notes_for(chud_id, session.notes, session.knowledge)
        answer = await run_test_taker(ChudTestInput(profile=profile, question=question, retained_notes=retained))
        marked = await run_examiner(ExaminerInput(question=question, answer=answer.answer))
        return Attempt(
            id=str(uuid.uuid4()),
            question_id=question.id,
            chud_id=chud_id,
            answer=answer.answer,
            marks=marked.marks,
            score=marked.total_score,
            max_score=question.marks,
            round=round_no,
        )

    attempts = await asyncio.gather(*(attempt_for(chud_id) for chud_id in session.chud_ids))
    session.attempts.extend(attempts)
    if session.mode == "TEST":
        http_transition(session, "REVIEW", "all_attempts_graded")
    coach = await run_coach(CoachInput(attempts=attempts, question=question, transcript=session.transcript, notes=session.notes, knowledge=session.knowledge))
    summary = {
        "round": round_no,
        "average": round(sum(attempt.score for attempt in attempts) / max(len(attempts), 1), 2),
        "max_score": question.marks,
        "full_marks": all(attempt.score == attempt.max_score for attempt in attempts),
    }
    feedback = {**coach.model_dump(), "question_id": question.id, "class_summary": summary}
    session.feedback.append(feedback)
    maybe_escalate(session)
    save_session(session)
    return {"question": question, "attempts": attempts, "class_summary": summary}


async def review(session: Session) -> dict:
    if not session.feedback:
        question = get_question(session.pack_id, session.current_question_id)
        attempts = [attempt for attempt in session.attempts if attempt.question_id == question.id]
        coach = await run_coach(CoachInput(attempts=attempts, question=question, transcript=session.transcript, notes=session.notes, knowledge=session.knowledge))
        feedback = {**coach.model_dump(), "question_id": question.id}
        session.feedback.append(feedback)
        save_session(session)
    return session.feedback[-1]


def begin_reteach(session: Session) -> dict:
    if session.mode == "REVIEW":
        http_transition(session, "RETEACH", "teacher_reteach")
    if session.mode == "RETEACH":
        http_transition(session, "TEACH", "reteach_ready")
    save_session(session)
    return {"mode": session.mode, "prompt": "Re-teach the missed concepts with a reason, an example, and one repeat."}


def _select_chuds(session: Session, notes) -> list[str]:
    if not notes:
        return session.chud_ids[:1]
    scores = []
    note_ids = [note.id for note in notes]
    for chud_id in session.chud_ids:
        knowledge = session.knowledge[chud_id]
        note_scores = [knowledge.retention_scores.get(note_id, 1.0) for note_id in note_ids]
        scores.append((sum(note_scores) / len(note_scores), chud_id))
    scores.sort()
    selected = [scores[0][1]]
    if session.turn % 3 == 0 and len(scores) > 1:
        selected.append(scores[1][1])
    return selected

