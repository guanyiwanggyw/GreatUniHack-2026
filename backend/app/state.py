from __future__ import annotations

import time
from dataclasses import dataclass

from fastapi import HTTPException

from .models import Mode, Session


ALLOWED: dict[str, set[str]] = {
    "TEACH": {"TEST", "ESCALATED"},
    "TEST": {"REVIEW", "ESCALATED"},
    "REVIEW": {"RETEACH", "FINISHED", "ESCALATED"},
    "RETEACH": {"TEACH", "ESCALATED"},
    "ESCALATED": {"TEACH"},
    "FINISHED": set(),
}


@dataclass
class IllegalTransition(Exception):
    current: str
    target: str
    allowed: set[str]


def allowed_transitions(mode: str) -> set[str]:
    return ALLOWED.get(mode, set())


def transition(session: Session, target: Mode, reason: str) -> Session:
    allowed = allowed_transitions(session.mode)
    if target not in allowed:
        raise IllegalTransition(session.mode, target, allowed)
    session.transitions.append(
        {
            "from": session.mode,
            "to": target,
            "reason": reason,
            "timestamp": time.time(),
        }
    )
    session.mode = target
    return session


def http_transition(session: Session, target: Mode, reason: str) -> Session:
    try:
        return transition(session, target, reason)
    except IllegalTransition as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "current": exc.current,
                "target": exc.target,
                "allowed": sorted(exc.allowed),
            },
        ) from exc

