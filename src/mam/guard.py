"""Quarantine for fragments of untrusted content that look like instructions.

Untrusted text (tool output, documents) is data, not commands. A line
is held back if it has a sign of prompt injection: it addresses the agent or an AI,
tells it to ignore or override the rules, refers to system authority, or sets
behavior for future sessions. Ordinary imperative phrases ("forward the log", "send
the protocol", "always put the office in copy") are data; we do not touch them.
Known limitations: a simple attack without these markers passes; a harmless line with a
marker ("from now on the sync is on Thursday") is blocked. Both costs are measured.
"""
from __future__ import annotations

import re

# Signs of an instruction addressed to the model. Case does not matter (re.I).
# Groups, in order: an address to the assistant/AI; "ignore the rules/instructions";
# "ignore everything above"; "from now on" and "in future sessions";
# "new instructions" and "system prompt"; a direct order "you must/should/will".
_INSTRUCTION = re.compile(
    r"\b(automated assistants?|ai (?:agents?|assistants?|systems?)|language models?|assistants? reading"
    r"|(?:ignore|disregard|forget|override)\b[^.\n]{0,40}\b(?:rules?|instructions?|polic(?:y|ies)|guidelines|configuration)"
    r"|(?:ignore|disregard)\s+(?:all |every |any )?(?:earlier|previous|prior|above)"
    r"|from now on|in (?:all )?(?:future|following) sessions?"
    r"|new instructions?|system (?:prompt|override|notice)"
    r"|you (?:must|should|will|are to))\b",
    re.I)

def fragments(text: str) -> list[str]:
    """Splits the text into lines (a list marker is not counted). This is the unit of quarantine:
    a line with an injected instruction is held back as a whole, not sentence by sentence."""
    return [ln for ln in (raw.strip().lstrip("-*").strip() for raw in text.split("\n")) if ln]

def split_untrusted(text: str) -> tuple[list[str], list[str]]:
    """Returns (the fragments kept, the fragments held back in quarantine)."""
    kept, held = [], []
    for frag in fragments(text):
        (held if _INSTRUCTION.search(frag) else kept).append(frag)
    return kept, held
