"""Answer bank + unanswered question queue (JSON files for Phase 1)."""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime

ANSWERS_FILE = Path("data/answers.json")
UNANSWERED_FILE = Path("data/unanswered.json")


def load_answers() -> dict:
    if ANSWERS_FILE.exists():
        return json.loads(ANSWERS_FILE.read_text(encoding="utf-8"))
    return {}


def save_answers(answers: dict) -> None:
    ANSWERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    ANSWERS_FILE.write_text(
        json.dumps(answers, ensure_ascii=False, indent=2), encoding="utf-8")


def add_unanswered(items: list) -> None:
    if not items:
        return
    existing = load_unanswered()
    seen = {u["question"].lower() for u in existing}
    for it in items:
        q = it["question"] if isinstance(it, dict) else it.question
        if q.lower() in seen:
            continue
        if isinstance(it, dict):
            existing.append(it)
        else:
            existing.append(it.model_dump(mode="json"))
        seen.add(q.lower())
    UNANSWERED_FILE.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8")


def load_unanswered() -> list:
    if UNANSWERED_FILE.exists():
        return json.loads(UNANSWERED_FILE.read_text(encoding="utf-8"))
    return []


def clear_unanswered() -> None:
    UNANSWERED_FILE.write_text("[]", encoding="utf-8")


def resolve_unanswered(question: str, answer: str) -> None:
    """Move from unanswered → answers, removing from queue."""
    answers = load_answers()
    answers[question] = answer
    save_answers(answers)
    rest = [u for u in load_unanswered() if u["question"] != question]
    UNANSWERED_FILE.write_text(
        json.dumps(rest, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8")
