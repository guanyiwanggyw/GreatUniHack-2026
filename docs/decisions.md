# Decisions

- The repository was empty, so the prototype is scaffolded as a compact full-stack app under the requested structure.
- Mock mode is the default whenever API keys are absent. Mock agents use deterministic heuristics so tests and eval can run without network access.
- The optional SQLite persistence layer is not implemented in the hackathon scaffold; the in-memory store is kept behind simple session-store functions so persistence can be added later.
- Sample content is original prototype content and is clearly marked for replacement with real exam-board material.
- Voice is turn-based: browser audio upload, ElevenLabs STT wrapper, agent pipeline, then per-chud ElevenLabs TTS wrapper.
- Paper ingest accepts uploaded files only and returns editable draft questions seeded from the current pack in mock mode.
- The eval runner teaches canned scripts one non-empty line at a time with fixed eval session ids. This keeps the evidence reproducible while matching the app's turn-based teaching loop.

