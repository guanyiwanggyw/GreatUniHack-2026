from __future__ import annotations

import os
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent
CONTENT_DIR = REPO_DIR / "content" / "packs"
GENERATED_DIR = BACKEND_DIR / ".generated"
AUDIO_DIR = GENERATED_DIR / "audio"


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def mock_mode() -> bool:
    explicit = os.getenv("MOCK_MODE")
    if explicit is not None:
        return explicit == "1"
    return not bool(os.getenv("LLM_API_KEY") or os.getenv("ELEVENLABS_API_KEY"))


AUDIO_DIR.mkdir(parents=True, exist_ok=True)

