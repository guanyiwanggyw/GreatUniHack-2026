# SPEC

Teach-Chud is now a one-student whiteboard teaching app.

The teacher talks naturally. Phrases appear live on a whiteboard, can be corrected before commit, and are grouped into teaching segments. Only committed segments enter the teach pipeline.

There is exactly one student: Chud. Chud listens, reacts after natural segment boundaries, can recap remembered notes, can be tested, and can escalate to a tutor when stuck.

Milestones:

- R1 Single Chud: replace the multi-student model with one profile in `content/chud.json`. Done.
- R2 Live transcription pipeline: phrase-level `/api/stt`, segment commits to teach, typed fallback. In progress.
- R3 Whiteboard + Chud UI: board, sticky notes, Chud avatar, caption and dock. In progress.
- R4 Purple design system: tokenized dark-purple chrome and bright board. In progress.
- R5 Brain drawer, recap, exam panel polish. In progress.
- R6 Drawing flag: optional `VITE_ENABLE_DRAWING=true`; not required for baseline.

Earlier multi-student milestones are considered complete and superseded.
