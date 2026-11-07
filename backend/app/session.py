from __future__ import annotations

import time
import uuid
from typing import Any

from .content import get_question
from .models import ChudKnowledge, Escalation, Session
from .profiles import list_profiles


SESSIONS: dict[str, Session] = {}
ESCALATIONS: dict[str, Escalation] = {}


def create_session(pack_id: str, chud_ids: list[str] | None = None) -> Session:
    if chud_ids is None:
        chud_ids = [profile.id for profile in list_profiles()]
    session_id = str(uuid.uuid4())
    question = get_question(pack_id)
    session = Session(
        id=session_id,
        pack_id=pack_id,
        chud_ids=chud_ids,
        current_question_id=question.id,
        knowledge={cid: ChudKnowledge(chud_id=cid) for cid in chud_ids},
        transitions=[
            {
                "from": None,
                "to": "TEACH",
                "reason": "session_created",
                "timestamp": time.time(),
            }
        ],
    )
    SESSIONS[session_id] = session
    return session


def get_session(session_id: str) -> Session:
    if session_id not in SESSIONS:
        raise KeyError(session_id)
    return SESSIONS[session_id]


def save_session(session: Session) -> Session:
    SESSIONS[session.id] = session
    return session


def add_escalation(escalation: Escalation) -> Escalation:
    ESCALATIONS[escalation.id] = escalation
    return escalation


def get_escalation(escalation_id: str) -> Escalation:
    if escalation_id not in ESCALATIONS:
        raise KeyError(escalation_id)
    return ESCALATIONS[escalation_id]


def list_open_escalations() -> list[Escalation]:
    return [esc for esc in ESCALATIONS.values() if esc.status == "open"]


def reset_store() -> None:
    SESSIONS.clear()
    ESCALATIONS.clear()

