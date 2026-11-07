# API

- `GET /api/health` returns `{ok, mock_mode}`.
- `GET /api/packs` lists subject packs.
- `GET /api/chud` returns the single Chud profile.
- `POST /api/stt` accepts multipart `audio` and optional `mime`; returns `{text, words, duration_ms}`.
- `POST /api/sessions` starts a session for one Chud.
- `GET /api/sessions/{id}` returns session state.
- `POST /api/sessions/{id}/teach` accepts `{text, source, words?}` and returns transcript, pipeline, notes, reply text, reply audio, emotion, knowledge, metrics and mode.
- `POST /api/sessions/{id}/chud/recap` returns Chud's recap text, audio URL and emotion.
- `GET /api/sessions/{id}/brain` returns notes, concept coverage, understanding and last score.
- `POST /api/sessions/{id}/test` returns one question, one attempt and a summary.
- `GET /api/sessions/{id}/review` returns Coach feedback.
- `POST /api/sessions/{id}/reteach` returns to teaching.
- `POST /api/ingest`, `POST /api/packs/{id}/questions`, `GET /api/escalations`, `POST /api/escalations/{id}/reply` remain available from settings.
