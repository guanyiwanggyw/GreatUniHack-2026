# Teach-Chud

Teach-Chud is a hackathon prototype where a human teaches one AI student, Chud, at a whiteboard. Chud only answers from remembered notes extracted from committed teaching segments.

The default setup runs in `MOCK_MODE=1`, so the demo works without API keys.

## Run

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -r backend/requirements.txt
cd frontend && npm install && cd ..
make dev
```

Backend: `http://127.0.0.1:8000`
Frontend: `http://127.0.0.1:5173`

On Windows without `make`, run two terminals:

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm run dev -- --host 127.0.0.1
```

## Behaviour

- The teacher talks or types naturally.
- Phrase audio is transcribed through `POST /api/stt`.
- A segment is committed by silence, the Done button, or typed submit.
- Guardrail, Extractor, FactChecker, retention, Chud, output guardrail and TTS run after each committed segment.
- Chud can recap remembered notes from the brain drawer.
- Testing returns one answer, one marked attempt and Coach diagnostics.

## Environment

Copy `.env.example` to `.env` and set real keys only when needed. Do not commit `.env`.

Every LLM request goes through `backend/app/llm.py::llm`. ElevenLabs STT/TTS are wrapped in `backend/app/stt.py` and `backend/app/tts.py`.

## Content

The included A-level Computer Science algorithms pack is prototype content written for the prototype. Replace it with real past-paper questions before a formal educational deployment, and credit the relevant exam board.

## Test And Eval

```bash
make test
make eval
```

## Browser Testing With Playwright MCP

`.mcp.json` registers the Playwright MCP server for Claude Code. Open Claude Code from this folder and approve the `playwright` server when asked.

The MCP browser uses `playwright-mcp.config.json`. Its init script, `e2e/fake-microphone.js`, replaces the microphone with a recorded teaching clip: about 11 seconds of a binary-search explanation, then 5 seconds of silence, on loop. That lets Claude test the voice flow without a real microphone. Screenshots and other MCP output go to `.playwright-mcp/`, which is gitignored.
