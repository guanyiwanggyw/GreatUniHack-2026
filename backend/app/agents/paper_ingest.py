from __future__ import annotations

import time

from pydantic import BaseModel

from ..agent_logging import log_agent_call
from ..content import get_questions
from ..models import Question


class PaperIngestInput(BaseModel):
    paper_text: str
    mark_scheme_text: str
    pack_id: str


class PaperIngestOutput(BaseModel):
    draft_questions: list[Question]


async def run_paper_ingest(payload: PaperIngestInput) -> PaperIngestOutput:
    started = time.perf_counter()
    seed = get_questions(payload.pack_id)
    drafts = []
    for index, question in enumerate(seed[:2], start=1):
        clone = question.model_copy(deep=True)
        clone.id = f"draft-{index}"
        clone.text = f"[Draft from upload] {clone.text}"
        drafts.append(clone)
    log_agent_call("paper_ingest", int((time.perf_counter() - started) * 1000), len(payload.paper_text) + len(payload.mark_scheme_text), "mock_draft")
    return PaperIngestOutput(draft_questions=drafts)

