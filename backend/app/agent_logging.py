from __future__ import annotations

import time
from collections import deque
from typing import Any

_LOGS: deque[dict[str, Any]] = deque(maxlen=200)


def log_agent_call(agent: str, latency_ms: int, input_size: int, outcome: str, detail: str = "") -> None:
    _LOGS.appendleft(
        {
            "timestamp": time.time(),
            "agent": agent,
            "latency_ms": latency_ms,
            "input_size": input_size,
            "outcome": outcome,
            "detail": detail,
        }
    )


def recent_logs() -> list[dict[str, Any]]:
    return list(_LOGS)

