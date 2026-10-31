"""Fact extractors for the memory level: oracle, rules and replay of saved model answers.

Pinned constraints are found by one rule in every variant: the entry format carries
no oracle constraints. Rules never see implicit updates ("trimmed by 25 percent"),
which is the point of having them as a plain extractor.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from mam.types import Entry, Fact

DAY_ZERO = date(2026, 1, 5)
UNKNOWN_TIME = -1  # event time not stated in the text: the memory treats the fact as "latest write"


@dataclass(frozen=True)
class Extraction:
    facts: tuple[Fact, ...] = ()
    constraints: tuple[str, ...] = ()
    refused: bool = False  # the model refused; nothing was extracted


# ---- constraints -----------------------------------------------------------

_CONSTRAINT = re.compile(
    r"\b(never|must not|do not|don't|hard rule|standing instruction|from now on|whatever anyone asks)\b", re.I)
_SENTENCES = re.compile(r"(?<=[.!?])\s+|\n+")


def sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCES.split(text) if s.strip()]


def rule_constraints(entry: Entry, require_trusted: bool = True) -> tuple[str, ...]:
    """Standing rules stated by a trusted source (any source when the trust filter is off)."""
    if require_trusted and entry.trust != "trusted":
        return ()
    return tuple(s for s in sentences(entry.text) if _CONSTRAINT.search(s))


# ---- rules for facts -------------------------------------------------------

LABELS = {  # longest labels first
    "pilot user count": "user_count", "contingency reserve": "contingency_usd", "integration partner": "integration",
    "sign-off date": "sign_off_date", "handover date": "handover_date", "go-live date": "go_live_date",
    "uat start date": "uat_start_date", "risk buffer": "risk_buffer_usd", "data source": "data_source",
    "user count": "user_count", "tech lead": "tech_lead", "budget": "budget_usd", "owner": "owner",
}
_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_MONEY = re.compile(r"\bUSD\s*([\d,]+)")
_COUNT = re.compile(r"\b(\d{1,3}(?:,\d{3})+|\d+)\b")
_NAME = re.compile(r"\b([A-Z][a-z]+ [A-Z][a-z]+)\b")
_WORD = re.compile(r"(?:is|at|:|are)\s+([A-Z][a-z]+)\b")
_MODULE = re.compile(r"\b(?:the |For the )?([a-z][a-z-]*) module\b", re.I)
_PROJECT = re.compile(r"\b([A-Z][a-z]+) project\b")
_AS_OF = re.compile(r"as of (\d{4}-\d{2}-\d{2})")
_STATUS_HEAD = re.compile(r"^STATUS\s+(\S+)")
_NON_MODULE = {"the", "this", "that", "a", "each", "every", "same", "other"}


def _event_time(sentence: str) -> int:
    m = _AS_OF.search(sentence)
    return (date.fromisoformat(m.group(1)) - DAY_ZERO).days if m else UNKNOWN_TIME


def _source(sentence: str, entry: Entry) -> str:
    low = sentence.lower()
    if "per the vendor document" in low:
        return "document"
    if "per the status feed" in low:
        return "tool"
    if "per the user" in low:
        return "user"
    return {"user_message": "user", "tool_output": "tool", "document": "document"}.get(entry.kind, "agent")


def _value(attribute: str, sentence: str, after: int) -> str | None:
    tail = sentence[after:]
    if attribute.endswith("_date"):
        m = _DATE.search(tail)
        return m.group(0) if m else None
    if attribute.endswith("_usd"):
        m = _MONEY.search(tail)
        return m.group(1).replace(",", "") if m else None
    if attribute == "user_count":
        m = _COUNT.search(tail)
        return m.group(1).replace(",", "") if m else None
    if attribute in ("owner", "tech_lead"):
        m = _NAME.search(tail)
        return m.group(1) if m else None
    m = _WORD.search(tail)
    return m.group(1) if m else None


def rule_facts(entry: Entry) -> tuple[Fact, ...]:
    facts: list[Fact] = []
    status_entity = None
    for line in entry.text.split("\n"):
        h = _STATUS_HEAD.match(line)
        if h:
            status_entity = h.group(1)
            continue
        for sent in sentences(line) if status_entity is None else [line]:
            low = sent.lower()
            label = next((k for k in LABELS if k in low), None)
            if label is None:
                continue
            attribute = LABELS[label]
            value = _value(attribute, sent, low.index(label) + len(label))
            if value is None:
                continue
            mod = next((m.group(1) for m in _MODULE.finditer(sent) if m.group(1).lower() not in _NON_MODULE), None)
            proj = _PROJECT.search(sent)
            if status_entity:
                entity = status_entity
            elif mod:
                entity = f"Atlas/{mod}"
            else:
                entity = proj.group(1) if proj else "Atlas"
            facts.append(Fact(id=f"rx-{entry.id}-{len(facts)}", entity=entity, attribute=attribute, value=value,
                              valid_from=_event_time(sent), valid_to=None, supersedes=None,
                              source=_source(sent, entry)))
    return tuple(facts)


# ---- extractors ------------------------------------------------------------

class OracleExtractor:
    def extract(self, entry: Entry) -> Extraction:
        return Extraction(facts=entry.oracle_facts, constraints=rule_constraints(entry))


class RulesExtractor:
    def extract(self, entry: Entry) -> Extraction:
        return Extraction(facts=rule_facts(entry), constraints=rule_constraints(entry))


class CacheExtractor:
    """Replays saved model answers: one JSON line per entry id.

    {"entry_id": "...", "facts": [{"entity", "attribute", "value", "event_time", "source"}],
     "constraints": ["..."], "refusal": false}
    An entry that is missing from the cache yields nothing (counted as a missed extraction).
    """

    def __init__(self, path):
        self._rows: dict[str, dict] = {}
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                self._rows[row["entry_id"]] = row

    def extract(self, entry: Entry) -> Extraction:
        row = self._rows.get(entry.id)
        if row is None:
            return Extraction()
        if row.get("refusal"):
            return Extraction(refused=True)
        facts = tuple(
            Fact(id=f"cx-{entry.id}-{i}", entity=f["entity"], attribute=f["attribute"], value=str(f["value"]),
                 valid_from=int(f.get("event_time", UNKNOWN_TIME)), valid_to=None, supersedes=None,
                 source=f.get("source", "agent"))
            for i, f in enumerate(row.get("facts", [])))
        return Extraction(facts=facts, constraints=tuple(row.get("constraints", ())))


def make_extractor(kind: str, cache_path=None):
    if kind == "oracle":
        return OracleExtractor()
    if kind == "rules":
        return RulesExtractor()
    if kind == "cache":
        if cache_path is None:
            raise ValueError("extractor 'cache' needs cache_path")
        return CacheExtractor(cache_path)
    raise ValueError(f"unknown extractor: {kind}")
