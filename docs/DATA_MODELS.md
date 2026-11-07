# DATA MODELS

`Session` has `chud_id: "chud"`, one `ChudKnowledge`, a transcript, notes, attempts, feedback, metrics and transitions.

`ChudProfile` comes from `content/chud.json` and contains `method_weights`, `attention_span`, `question_style` and `persona`.

`TeachResponse` returns one Chud reply with `reply_text`, `reply_audio_url` and `emotion`.

`TestResponse` returns one `Attempt`.

`BrainView` contains remembered notes, concept coverage (`UNTAUGHT`, `SHAKY`, `SOLID`), `understanding`, `last_score` and `show_correctness`.

Correctness chips are hidden until after the first review.
