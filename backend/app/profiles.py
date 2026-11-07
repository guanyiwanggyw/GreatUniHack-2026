from __future__ import annotations

import json

from .config import REPO_DIR
from .models import ChudProfile


CHUD_PATH = REPO_DIR / "content" / "chud.json"


def get_profile(chud_id: str = "chud") -> ChudProfile:
    profile = ChudProfile.model_validate(json.loads(CHUD_PATH.read_text(encoding="utf-8")))
    if profile.id != chud_id:
        raise KeyError(chud_id)
    return profile


def list_profiles() -> list[ChudProfile]:
    return [get_profile()]
