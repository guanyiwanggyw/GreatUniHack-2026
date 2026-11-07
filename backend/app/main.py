from __future__ import annotations

import io
from pathlib import Path
import json

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pypdf import PdfReader

from .agent_logging import recent_logs
from .agents.paper_ingest import PaperIngestInput, run_paper_ingest
from .config import AUDIO_DIR, DEFAULT_PACK_ID, llm_available, voice_available
from .content import concept_names, delete_paper, get_pack, get_paper, get_questions, list_packs, list_papers, save_paper, save_questions
from .escalation import tutor_note_from_reply
from .models import Question
from .orchestrator import begin_reteach, brain_view, recap, review, run_test, sit_paper, teach_turn
from .profiles import get_profile
from .retention import recompute_knowledge
from .session import create_session, get_escalation, get_session, list_open_escalations, save_session
from .state import http_transition
from .stt import transcribe_audio, typed_result
from .tts import synthesize_speech

app = FastAPI(title="Teach-Chud")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    # mock_mode tells the frontend whether real speech-to-text is available; llm says whether agents use the AI.
    return {"ok": True, "mock_mode": not voice_available(), "voice": voice_available(), "llm": llm_available(), "default_pack": DEFAULT_PACK_ID}


@app.get("/api/packs")
async def packs():
    return {"packs": list_packs()}


@app.get("/api/chud")
async def chud_profile():
    return {"chud": get_profile()}


@app.get("/api/profiles")
async def profiles_compat():
    return {"profiles": [get_profile()]}


@app.get("/api/packs/{pack_id}/questions")
async def pack_questions(pack_id: str):
    return {"questions": get_questions(pack_id)}


@app.post("/api/sessions")
async def start_session(payload: dict):
    pack_id = payload.get("pack_id") or DEFAULT_PACK_ID
    session = create_session(pack_id)
    intro = "I'm Chud. Tap me any time and I'll say what I remember."
    audio_url = await synthesize_speech(intro, get_profile().voice_id, "chud")
    save_session(session)
    return {"session": session, "intro_line": {"text": intro, "audio_url": audio_url, "emotion": "HAPPY"}}


@app.post("/api/session")
async def start_session_compat(payload: dict):
    return await start_session(payload)


@app.post("/api/stt")
async def stt(audio: UploadFile = File(...), mime: str = Form("")):
    data = await audio.read()
    result = await transcribe_audio(audio.filename or "audio.webm", data, mime or audio.content_type, keyterms=list(concept_names(DEFAULT_PACK_ID).values()))
    return {"text": result.text, "words": result.words, "duration_ms": result.duration_ms}


@app.post("/api/sessions/{session_id}/teach")
async def teach(session_id: str, request: Request):
    session = _session_or_404(session_id)
    content_type = request.headers.get("content-type", "")
    source = "TYPED"
    words = []
    if "multipart/form-data" in content_type:
        form = await request.form()
        text = str(form.get("text", "")).strip()
        source = str(form.get("source", "VOICE"))
        words = _parse_words(form.get("words"))
    else:
        payload = await request.json()
        text = str(payload.get("text", "")).strip()
        source = str(payload.get("source", "TYPED"))
        words = payload.get("words") or []
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    return await teach_turn(session, typed_result(text, words), source=source)


@app.post("/api/session/{session_id}/teach")
async def teach_compat(session_id: str, request: Request):
    return await teach(session_id, request)


@app.post("/api/sessions/{session_id}/test")
async def test_chud(session_id: str, payload: dict | None = None):
    session = _session_or_404(session_id)
    return await run_test(session, (payload or {}).get("question_id"))


@app.post("/api/session/{session_id}/test")
async def test_chud_compat(session_id: str, payload: dict | None = None):
    return await test_chud(session_id, payload)


@app.get("/api/sessions/{session_id}/review")
async def get_review(session_id: str):
    session = _session_or_404(session_id)
    return await review(session)


@app.get("/api/session/{session_id}/review")
async def get_review_compat(session_id: str):
    return await get_review(session_id)


@app.post("/api/sessions/{session_id}/reteach")
async def reteach(session_id: str):
    session = _session_or_404(session_id)
    return begin_reteach(session)


@app.post("/api/session/{session_id}/reteach")
async def reteach_compat(session_id: str):
    return await reteach(session_id)


@app.post("/api/sessions/{session_id}/chud/recap")
async def chud_recap(session_id: str):
    session = _session_or_404(session_id)
    if session.mode not in ("TEACH", "RETEACH"):
        raise HTTPException(status_code=409, detail="Recap is only available while teaching.")
    return await recap(session)


@app.get("/api/sessions/{session_id}/brain")
async def brain(session_id: str):
    return brain_view(_session_or_404(session_id))


@app.get("/api/sessions/{session_id}")
async def get_state(session_id: str):
    return {"session": _session_or_404(session_id)}


@app.get("/api/session/{session_id}")
async def get_state_compat(session_id: str):
    return await get_state(session_id)


@app.get("/api/audio/{file}")
async def audio(file: str):
    path = AUDIO_DIR / Path(file).name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio not found")
    return Response(path.read_bytes(), media_type="audio/mpeg")


MAX_UPLOAD_BYTES = 25 * 1024 * 1024


@app.post("/api/ingest")
async def ingest(paper: UploadFile = File(...), mark_scheme: UploadFile = File(...), pack_id: str = Form(DEFAULT_PACK_ID)):
    _pack_or_404(pack_id)
    paper_text = await _read_upload_text(paper, "past paper")
    mark_text = await _read_upload_text(mark_scheme, "mark scheme")
    return await run_paper_ingest(PaperIngestInput(paper_text=paper_text, mark_scheme_text=mark_text, pack_id=pack_id, paper_filename=paper.filename or ""))


@app.get("/api/packs/{pack_id}/papers")
async def papers(pack_id: str):
    _pack_or_404(pack_id)
    return {"papers": list_papers(pack_id)}


@app.post("/api/packs/{pack_id}/papers")
async def create_paper(pack_id: str, payload: dict):
    _pack_or_404(pack_id)
    questions = [Question.model_validate(item) for item in payload.get("questions", [])]
    if not questions:
        raise HTTPException(status_code=400, detail="No questions supplied")
    paper = save_paper(pack_id, str(payload.get("title", "")), questions, [str(name) for name in payload.get("source_files", [])])
    return {"paper": paper}


@app.get("/api/packs/{pack_id}/papers/{paper_id}")
async def paper_detail(pack_id: str, paper_id: str):
    try:
        return {"paper": get_paper(pack_id, paper_id)}
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Paper not found") from error


@app.delete("/api/packs/{pack_id}/papers/{paper_id}")
async def remove_paper(pack_id: str, paper_id: str):
    try:
        delete_paper(pack_id, paper_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Paper not found") from error
    return {"ok": True}


@app.post("/api/sessions/{session_id}/papers/{paper_id}/sit")
async def sit(session_id: str, paper_id: str):
    session = _session_or_404(session_id)
    try:
        attempt = await sit_paper(session, paper_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Paper not found for this session's subject") from error
    return {"attempt": attempt, "session": session}


@app.post("/api/packs/{pack_id}/questions")
async def save_pack_questions(pack_id: str, payload: dict):
    questions = [Question.model_validate(item) for item in payload.get("questions", [])]
    if not questions:
        raise HTTPException(status_code=400, detail="No questions supplied")
    save_questions(pack_id, questions)
    return {"ok": True, "count": len(questions)}


@app.get("/api/escalations")
async def escalations():
    return {"escalations": list_open_escalations()}


@app.post("/api/escalations/{escalation_id}/reply")
async def escalation_reply(escalation_id: str, payload: dict):
    escalation = get_escalation(escalation_id)
    session = get_session(escalation.session_id)
    hint = payload.get("hint", "").strip()
    if not hint:
        raise HTTPException(status_code=400, detail="Hint is required")
    note = tutor_note_from_reply(session, hint)
    session.turn += 1
    note.turn = session.turn
    session.notes.append(note)
    session.transcript.append({"role": "tutor", "speaker": "Tutor", "text": hint})
    session.knowledge = recompute_knowledge(session.id, session.notes, session.turn)
    if note.id not in session.knowledge.retained_note_ids:
        session.knowledge.retained_note_ids.append(note.id)
    escalation.status = "resolved"
    escalation.tutor_reply = hint
    http_transition(session, "TEACH", "tutor_replied")
    save_session(session)
    return {"ok": True, "session": session}


@app.get("/api/debug/logs")
async def logs():
    return {"logs": recent_logs()}


def _session_or_404(session_id: str):
    try:
        return get_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Session not found") from exc


def _parse_words(raw) -> list[dict]:
    if raw is None or raw == "":
        return []
    if isinstance(raw, list):
        return raw
    try:
        parsed = json.loads(str(raw))
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _pack_or_404(pack_id: str):
    try:
        return get_pack(pack_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=f"Unknown subject pack {pack_id}") from error


async def _read_upload_text(upload: UploadFile, label: str = "file") -> str:
    data = await upload.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"The {label} is larger than 25 MB.")
    is_pdf = data[:5] == b"%PDF-" or (upload.filename or "").lower().endswith(".pdf")
    if is_pdf:
        try:
            reader = PdfReader(io.BytesIO(data))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as error:  # noqa: BLE001 - pypdf raises many error types for bad files
            raise HTTPException(status_code=400, detail=f"Could not read the {label} PDF: {error}") from error
    return data.decode("utf-8", errors="ignore")
