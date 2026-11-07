# BUILD ORDER

- R1 Single Chud: backend model, content profile, tests.
- R2 Live transcription: `/api/stt`, frontend listening hook, VAD config, phrase ordering, segment commit.
- R3 Whiteboard + Chud UI: board state hook, sticky notes, SVG avatar, captions, dock.
- R4 Purple design system: tokens, chrome, board, panels, accessibility states.
- R5 Brain and exam polish: recap, brain drawer, single-attempt exam panel, Coach diagnostics.
- R6 Drawing flag: optional canvas layer behind board writing and `board_image` upload.

Keep the teach, test, mark and review loop runnable after every step.
