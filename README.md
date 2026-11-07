# Teach-Chud

Teach-Chud is a hackathon prototype where a human teaches a class of AI students ("chuds"). The chuds only answer from notes extracted from the human's teaching, then an examiner marks their answers against a sample mark scheme.

The default setup runs in `MOCK_MODE=1`, so the full demo works without API keys.

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

## Environment

Copy `.env.example` to `.env` and set real keys only when needed. Do not commit `.env`.

Every LLM request goes through `backend/app/llm.py::llm`. ElevenLabs STT/TTS are wrapped in `backend/app/stt.py` and `backend/app/tts.py`. Voice model IDs and voice IDs are environment-configurable.

## Learner Profile Framing

Sam, Priya, Leo, Mia and Ollie are learner profiles such as "needs reasons", "needs examples", or "short attention". They are not VARK-style learning styles, which should not be used as an evidence claim in the pitch.

## Content

The included A-level Computer Science algorithms pack is sample content written for the prototype. Replace it with real past-paper questions before a public educational deployment, and credit the relevant exam board.

## Test And Eval

```bash
make test
make eval
```

The eval writes `docs/eval_results.md` and is designed to show good teaching scoring above vague teaching, which scores above confidently wrong teaching.

