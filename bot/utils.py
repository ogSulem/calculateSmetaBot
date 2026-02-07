from __future__ import annotations

from typing import Iterable


def rub(amount: float | int) -> str:
    value = int(round(float(amount)))
    return f"{value:,}".replace(",", " ") + " ₽"


def safe_float(text: str) -> float | None:
    try:
        return float(text.replace(" ", "").replace(",", "."))
    except ValueError:
        return None


def fmt_lines(lines: Iterable[str]) -> str:
    return "\n".join([x for x in lines if x])
