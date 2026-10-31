"""Quarantine for instruction-like fragments of untrusted content.

Untrusted text (tool output, documents) is data. Fragments that address an agent,
tell it to drop earlier rules, persist a behaviour, or send something somewhere are
held back from the context. The patterns are generic phrasings of prompt injection;
a benign sentence that happens to use them is blocked too (a false block), and
that cost is measured.
"""
from __future__ import annotations

import re

_INSTRUCTION = re.compile(
    r"\b(automated assistants?|ai (?:agents?|assistants?|systems?)|language models?"
    r"|ignore (?:all |every |any )?(?:earlier|previous|prior|above)|disregard|override"
    r"|from now on|in (?:all )?(?:future|following) sessions?|new instructions?"
    r"|system (?:prompt|override|notice)|you (?:must|should|will|are to)"
    r"|e-?mail|mail (?:the|a|all|it)|forward (?:the|all|it)|exfiltrat\w*"
    r"|set approval mode|approve (?:all|every)\w*)\b",
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
