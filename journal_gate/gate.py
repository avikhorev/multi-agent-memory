"""The gate in front of update_record: a check by code, then one model call that can only forbid with a quote."""
import json
import re
from dataclasses import dataclass

STAGES = ("unread_source", "user_rule", "gate_error", "unverified_refusal", "passed")
SYSTEM = (
    "You check one proposed change to the project record against the user's messages. A later message overrides "
    "an earlier one. Block the change only if a standing instruction that is still in force forbids it. A one-time "
    "request, a fact or a plan is not a prohibition. If the user asked for this change, or lifted the ban, allow it. "
    'Reply with one strict JSON object: {"allow": true or false, "quote": "the user\'s exact words that forbid it, '
    'empty when allowed", "reason": "at most 12 words"}.')


@dataclass(frozen=True)
class Decision:
    allow: bool
    stage: str
    reason: str = ""
    quote: str = ""


def _words(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _verified(quote: str, user_messages: list) -> bool:
    """Every word of the quote occurs in one single user message."""
    words = _words(quote)
    return bool(words) and any(set(words) <= set(_words(text)) for _, text in user_messages)


def _parse(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.S)
    try:
        obj = json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) and isinstance(obj.get("allow"), bool) else None


class Gate:
    def __init__(self, llm):
        self.llm = llm
        self.calls = []  # LLMResult of every model call, for the cost

    def check(self, action: dict, user_messages: list, source_offered: bool, source_read: bool) -> Decision:
        if source_offered and not source_read:
            return Decision(False, "unread_source", "Read the listed data source first; you may repeat this change "
                                                    "afterwards.")
        messages = "\n".join(f"[session {s}] {t}" for s, t in user_messages) or "(none)"
        prompt = (f"USER MESSAGES, OLDEST FIRST\n{messages}\n\nPROPOSED CHANGE\nfield: {action.get('field')}\n"
                  f"value: {action.get('value')}\n\nReply with the JSON object only.")
        verdict = None
        for _ in range(2):
            out = self.llm.complete(SYSTEM, [{"role": "user", "content": prompt}], {})
            self.calls.append(out)
            verdict = None if out.refusal else _parse(out.text)
            if verdict is not None:
                break
        if verdict is None:
            return Decision(False, "gate_error", "The gate could not check this change.")
        quote, reason = str(verdict.get("quote") or ""), str(verdict.get("reason") or "")
        if verdict["allow"]:
            return Decision(True, "passed", reason)
        if _verified(quote, user_messages):
            return Decision(False, "user_rule", reason, quote)
        return Decision(True, "unverified_refusal", reason, quote)
