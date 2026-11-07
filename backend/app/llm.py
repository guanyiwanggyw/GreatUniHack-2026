from __future__ import annotations

import json
import re
import time
from typing import Any

import httpx

from .agent_logging import log_agent_call
from .config import env, llm_available


class LLMUnavailable(RuntimeError):
    """Raised when no LLM is configured, so callers can fall back to their offline heuristics."""


async def llm(
    system: str,
    messages: list[dict[str, str]],
    json_schema: dict[str, Any] | None = None,
    timeout: float = 60,
    agent: str = "llm",
) -> dict[str, Any] | str:
    started = time.perf_counter()
    input_size = len(system) + sum(len(message.get("content", "")) for message in messages)
    if not llm_available():
        log_agent_call(agent, int((time.perf_counter() - started) * 1000), input_size, "mock")
        raise LLMUnavailable("No LLM configured")

    api_key = env("LLM_API_KEY")
    base_url = env("LLM_BASE_URL", "https://api.openai.com/v1/chat/completions")
    model = env("LLM_MODEL", "gpt-4o-mini")
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "system", "content": system}, *messages],
        "temperature": 0,
    }
    if json_schema:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "agent_response", "schema": json_schema},
        }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(base_url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    content = data["choices"][0]["message"]["content"]
    log_agent_call(agent, int((time.perf_counter() - started) * 1000), input_size, "ok")
    if json_schema:
        return _parse_json(content)
    return content


def _parse_json(content: str) -> dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.S)
        if not match:
            raise
        return json.loads(match.group(0))
