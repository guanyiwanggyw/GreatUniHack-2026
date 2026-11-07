# Architecture

```mermaid
flowchart LR
  UI[React Teacher Dashboard] --> API[FastAPI API]
  API --> STT[STT Wrapper]
  API --> Guard[Input Guardrail]
  Guard --> Extract[Extractor]
  Extract --> Fact[FactChecker]
  Fact --> Retain[Deterministic Retention]
  Retain --> Chud[Chud Reply/Test Agents]
  Chud --> Out[Output Guardrail]
  Out --> TTS[TTS Wrapper]
  API --> Exam[Examiner]
  Exam --> Coach[Coach]
  Coach --> Esc[Escalation Rule]
  Esc --> Tutor[Tutor Page]
  API --> Store[In-memory Session Store]
  API --> Content[Subject Packs]
```

All LLM access is routed through `backend/app/llm.py::llm`. Agent prompts live in `backend/app/prompts/`. The retention engine is deterministic Python code and is the key knowledge-isolation boundary.

