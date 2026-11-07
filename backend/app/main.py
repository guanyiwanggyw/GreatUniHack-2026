from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pypdf import PdfReader

from .agent_logging import recent_logs
from .agents.paper_ingest import PaperIngestInput, run_paper_ingest
from .config import AUDIO_DIR, mock_mode
from .content import get_questions, list_packs, save_questions
from .escalation import tutor_note_from_reply
from .models import Question
from .orchestrator import begin_reteach, review, run_test, teach_turn
from .profiles import list_profiles
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
    return {"ok": True, "mock_mode": mock_mode()}


@app.get("/api/packs")
async def packs():
    return {"packs": list_packs()}


@app.get("/api/profiles")
async def profiles():
    return {"profiles": list_profiles()}


@app.get("/api/packs/{pack_id}/questions")
async def pack_questions(pack_id: str):
    return {"questions": get_questions(pack_id)}


@app.post("/api/session")
async def start_session(payload: dict):
    pack_id = payload.get("pack_id", "alevel-cs-algorithms")
    session = create_session(pack_id, payload.get("chud_ids"))
    intro_lines = []
    for profile in list_profiles():
        if profile.id in session.chud_ids:
            text = f"I'm {profile.name}. {profile.questioning_style}"
            audio_url = await synthesize_speech(text, None, profile.id)
            intro_lines.append({"chud_id": profile.id, "text": text, "audio_url": audio_url})
    save_session(session)
    return {"session": session, "intro_lines": intro_lines}


@app.post("/api/session/{session_id}/teach")
async def teach(session_id: str, request: Request):
    session = _session_or_404(session_id)
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        audio = form.get("audio")
        if isinstance(audio, UploadFile):
            data = await audio.read()
            stt = await transcribe_audio(audio.filename or "audio.webm", data, audio.content_type)
        else:
            stt = typed_result(str(form.get("text", "")))
    else:
        payload = await request.json()
        stt = typed_result(payload.get("text", ""))
    return await teach_turn(session, stt)


@app.post("/api/session/{session_id}/test")
async def test_class(session_id: str, payload: dict | None = None):
    session = _session_or_404(session_id)
    return await run_test(session, (payload or {}).get("question_id"))


@app.get("/api/session/{session_id}/review")
async def get_review(session_id: str):
    session = _session_or_404(session_id)
    return await review(session)


@app.post("/api/session/{session_id}/reteach")
async def reteach(session_id: str):
    session = _session_or_404(session_id)
    return begin_reteach(session)


@app.get("/api/session/{session_id}")
async def get_state(session_id: str):
    return {"session": _session_or_404(session_id)}


@app.get("/api/audio/{file}")
async def audio(file: str):
    path = AUDIO_DIR / Path(file).name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio not found")
    return Response(path.read_bytes(), media_type="audio/mpeg")


@app.post("/api/ingest")
async def ingest(paper: UploadFile = File(...), mark_scheme: UploadFile = File(...), pack_id: str = "alevel-cs-algorithms"):
    paper_text = await _read_upload_text(paper)
    mark_text = await _read_upload_text(mark_scheme)
    return await run_paper_ingest(PaperIngestInput(paper_text=paper_text, mark_scheme_text=mark_text, pack_id=pack_id))


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
    session.knowledge = recompute_knowledge(session.id, session.chud_ids, session.notes, session.turn)
    for chud_id in session.chud_ids:
        if note.id not in session.knowledge[chud_id].retained_note_ids:
            session.knowledge[chud_id].retained_note_ids.append(note.id)
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


async def _read_upload_text(upload: UploadFile) -> str:
    data = await upload.read()
    if upload.filename and upload.filename.lower().endswith(".pdf"):
        temp = AUDIO_DIR / f"upload-{upload.filename}"
        temp.write_bytes(data)
        reader = PdfReader(str(temp))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return data.decode("utf-8", errors="ignore")

