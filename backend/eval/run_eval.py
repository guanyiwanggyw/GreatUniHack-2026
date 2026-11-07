from __future__ import annotations

import asyncio
from pathlib import Path

from app.content import get_questions
from app.orchestrator import run_test, teach_turn
from app.session import create_session, reset_store
from app.stt import typed_result


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = Path(__file__).parent / "scripts"
DOCS = ROOT / "docs"


async def run() -> str:
    rows = ["| script | question | chud | score | incorrect notes |", "|---|---|---|---:|---:|"]
    averages: dict[str, list[float]] = {}
    for script_name in ("good", "vague", "wrong"):
        text = (SCRIPTS / f"{script_name}.txt").read_text(encoding="utf-8")
        reset_store()
        session = create_session("alevel-cs-algorithms")
        session.id = f"eval-{script_name}"
        for line in [line.strip() for line in text.splitlines() if line.strip()]:
            await teach_turn(session, typed_result(line))
        incorrect = sum(1 for note in session.notes if note.status == "incorrect")
        for question in get_questions(session.pack_id):
            result = await run_test(session, question.id)
            for attempt in result["attempts"]:
                rows.append(f"| {script_name} | {question.id} | {attempt.chud_id} | {attempt.score}/{attempt.max_score} | {incorrect} |")
                averages.setdefault(script_name, []).append(attempt.score / attempt.max_score)
            session.mode = "TEACH"
    summary = ["", "## Summary", ""]
    for name, values in averages.items():
        summary.append(f"- {name}: {sum(values) / len(values):.2%} class average")
    output = "# Eval Results\n\n" + "\n".join(rows + summary) + "\n"
    DOCS.mkdir(exist_ok=True)
    (DOCS / "eval_results.md").write_text(output, encoding="utf-8")
    return output


if __name__ == "__main__":
    print(asyncio.run(run()))

