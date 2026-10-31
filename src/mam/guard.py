"""Quarantine for instruction-like fragments of untrusted content.

Untrusted text (tool output, documents) is data. A line is held back when it carries a
marker of prompt injection: it addresses an agent or an AI, tells the reader to ignore or
override rules, claims system authority, or sets behaviour for future sessions. Ordinary
imperatives ("forward the log", "email the minutes", "always copy the office") are data.
Known limits: a plain imperative attack with none of these markers passes; a benign line
that uses a marker ("from now on the sync is on Thursday") is blocked. Both costs are measured.
"""
from __future__ import annotations

import re

_INSTRUCTION = re.compile(
    r"\b(automated assistants?|ai (?:agents?|assistants?|systems?)|language models?|assistants? reading"
    r"|(?:ignore|disregard|forget|override)\b[^.\n]{0,40}\b(?:rules?|instructions?|polic(?:y|ies)|guidelines|configuration)"
    r"|(?:ignore|disregard)\s+(?:all |every |any )?(?:earlier|previous|prior|above)"
    r"|from now on|in (?:all )?(?:future|following) sessions?"
    r"|new instructions?|system (?:prompt|override|notice)"
    r"|you (?:must|should|will|are to))\b",
    re.I)


def fragments(text: str) -> list[str]:
    """Lines (a bullet is one unit): a line with an injected instruction is held back whole."""
    return [ln for ln in (raw.strip().lstrip("-*").strip() for raw in text.split("\n")) if ln]


def split_untrusted(text: str) -> tuple[list[str], list[str]]:
    """Return (kept fragments, quarantined fragments)."""
    kept, held = [], []
    for frag in fragments(text):
        (held if _INSTRUCTION.search(frag) else kept).append(frag)
    return kept, held
