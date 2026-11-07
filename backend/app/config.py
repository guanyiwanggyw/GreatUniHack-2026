from __future__ import annotations

import os
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent
CONTENT_DIR = REPO_DIR / "content" / "packs"
GENERATED_DIR = BACKEND_DIR / ".generated"
AUDIO_DIR = GENERATED_DIR / "audio"
UPLOAD_DIR = GENERATED_DIR / "uploads"


def _load_dotenv(path: Path) -> None:
    """Read KEY=VALUE lines from the repo's .env without overriding variables already set."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv(REPO_DIR / ".env")


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def _real_key(name: str) -> bool:
    value = os.getenv(name, "")
    return bool(value) and value != "replace_me"


def mock_mode() -> bool:
    """True when nothing external is configured. MOCK_MODE=1 forces everything offline."""
    explicit = os.getenv("MOCK_MODE")
    if explicit is not None:
        return explicit == "1"
    return not (_real_key("LLM_API_KEY") or _real_key("ELEVENLABS_API_KEY"))


def llm_available() -> bool:
    """Agents call the real LLM only when a key is set and MOCK_MODE is not forcing offline mode."""
    return os.getenv("MOCK_MODE") != "1" and _real_key("LLM_API_KEY")


def voice_available() -> bool:
    """Speech-to-text and text-to-speech use ElevenLabs only when its key is set and MOCK_MODE is not 1."""
    return os.getenv("MOCK_MODE") != "1" and _real_key("ELEVENLABS_API_KEY")


DEFAULT_PACK_ID = env("DEFAULT_PACK", "gcse-maths")

AUDIO_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
