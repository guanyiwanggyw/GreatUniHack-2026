from __future__ import annotations

FILLERS = {"um", "uh", "like", "basically", "sort", "sort of", "erm"}


def speech_metrics(text: str, words: list[dict] | None = None) -> dict:
    tokens = [token.strip(".,!?;:").lower() for token in text.split()]
    filler_count = sum(1 for token in tokens if token in FILLERS)
    pauses = 0
    wpm: float | str = "N/A"
    if words:
        starts = [float(word.get("start", 0)) for word in words if word.get("type", "word") == "word"]
        ends = [float(word.get("end", 0)) for word in words if word.get("type", "word") == "word"]
        if starts and ends and max(ends) > min(starts):
            duration_min = (max(ends) - min(starts)) / 60
            wpm = round(len(words) / duration_min, 1) if duration_min else "N/A"
        ordered = sorted(words, key=lambda item: float(item.get("start", 0)))
        for previous, current in zip(ordered, ordered[1:]):
            if float(current.get("start", 0)) - float(previous.get("end", 0)) > 2:
                pauses += 1
    return {
        "wpm": wpm,
        "filler_count": filler_count,
        "long_pauses": pauses,
        "word_count": len(tokens),
    }

