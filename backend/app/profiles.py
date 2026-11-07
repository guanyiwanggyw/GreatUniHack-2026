from __future__ import annotations

from .models import ChudProfile


PROFILES: list[ChudProfile] = [
    ChudProfile(
        id="sam",
        name="Sam",
        avatar="S",
        voice_id_env="ELEVENLABS_VOICE_SAM",
        description="Needs the reason",
        questioning_style="But why does that work?",
        base_rate=0.34,
        memory_span=5.0,
        weights={
            "has_reason": 0.34,
            "has_example": 0.05,
            "covers_edge_case": 0.04,
            "is_procedural_step": 0.03,
            "short_note": 0.05,
        },
    ),
    ChudProfile(
        id="priya",
        name="Priya",
        avatar="P",
        voice_id_env="ELEVENLABS_VOICE_PRIYA",
        description="Edge-case sceptic",
        questioning_style="What if the list is empty?",
        base_rate=0.32,
        memory_span=6.0,
        weights={
            "has_reason": 0.08,
            "has_example": 0.06,
            "covers_edge_case": 0.36,
            "is_procedural_step": 0.02,
            "short_note": 0.04,
        },
    ),
    ChudProfile(
        id="leo",
        name="Leo",
        avatar="L",
        voice_id_env="ELEVENLABS_VOICE_LEO",
        description="Needs worked examples",
        questioning_style="Can you show me with numbers?",
        base_rate=0.30,
        memory_span=5.5,
        weights={
            "has_reason": 0.06,
            "has_example": 0.38,
            "covers_edge_case": 0.03,
            "is_procedural_step": 0.06,
            "short_note": 0.04,
        },
    ),
    ChudProfile(
        id="mia",
        name="Mia",
        avatar="M",
        voice_id_env="ELEVENLABS_VOICE_MIA",
        description="Step-by-step",
        questioning_style="What comes after that step?",
        base_rate=0.35,
        memory_span=6.5,
        weights={
            "has_reason": 0.05,
            "has_example": 0.08,
            "covers_edge_case": 0.05,
            "is_procedural_step": 0.35,
            "short_note": 0.03,
        },
    ),
    ChudProfile(
        id="ollie",
        name="Ollie",
        avatar="O",
        voice_id_env="ELEVENLABS_VOICE_OLLIE",
        description="Short attention",
        questioning_style="Can you say that again?",
        base_rate=0.28,
        memory_span=2.3,
        weights={
            "has_reason": 0.05,
            "has_example": 0.06,
            "covers_edge_case": 0.04,
            "is_procedural_step": 0.07,
            "short_note": 0.18,
        },
    ),
]


def list_profiles() -> list[ChudProfile]:
    return PROFILES


def get_profile(chud_id: str) -> ChudProfile:
    for profile in PROFILES:
        if profile.id == chud_id:
            return profile
    raise KeyError(chud_id)

