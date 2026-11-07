# AGENTS

Architecture rules:

- Routes stay thin. FastAPI handlers parse HTTP input, call orchestration or services, and return typed data.
- `backend/app/orchestrator.py` owns the teach, recap, test, review and brain flows.
- Agents live in `backend/app/agents/`; each agent wraps one prompt-shaped responsibility and returns structured Pydantic data.
- Services wrap external systems: `llm.py`, `stt.py`, `tts.py`, content loading and session storage.
- Pure domain logic stays deterministic: retention, state transitions, escalation and metrics.
- Mock mode must run with no secrets. `MOCK_MODE=1` remains the default when keys are absent.
- Teacher text is untrusted data. Prompts must delimit it and Chud may only answer from remembered notes.
