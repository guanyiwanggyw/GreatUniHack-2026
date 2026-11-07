# Decisions

- The refactor keeps the existing FastAPI, Vite, agents, retention, voice wrappers and mock-mode architecture.
- There is exactly one profile in `content/chud.json`; session state stores `chud_id` and one `ChudKnowledge`.
- Phrase-level transcription is stateless at `POST /api/stt`; only committed segments run the teach pipeline.
- The board state hook derives UI from transcript and notes. It does not decide business logic.
- Correctness is hidden in the brain drawer until after review so the teacher is not corrected mid-explanation.
- Drawing remains a future optional `VITE_ENABLE_DRAWING=true` milestone and is not enabled in the baseline.
- The dirty saved `questions.json` draft is treated as current local content instead of being overwritten.
