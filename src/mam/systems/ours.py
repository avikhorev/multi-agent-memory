"""The structured memory: dated facts, scopes, conflict rules, quarantine and pinned constraints.

Facts are extracted once per session. At read time the versions visible to the reader
are resolved key by key in write order, so scopes, validity and trust can each be
switched off for ablations.
"""
from __future__ import annotations

from dataclasses import dataclass

from mam.extract import UNKNOWN_TIME, make_extractor, rule_constraints
from mam.guard import split_untrusted
from mam.systems.base import MemorySystem, make_context, visible_to
from mam.systems.ranking import bm25_scores
from mam.tokens import count
from mam.types import Context, ContextItem, Entry, Fact, Reader

AUTHORITY = {"user": 3, "tool": 2, "document": 1, "agent": 0}
TRUST = {"trusted": 2, "agent": 1, "untrusted": 0}


def _norm(text: str) -> str:
    return "".join(text.lower().replace(",", "").split())


@dataclass
class Version:
    fact: Fact
    entry: Entry
    time: int
    authority: int
    trust: int


class Ours(MemorySystem):
    def __init__(self, limit: int, ablate=frozenset(), extractor: str = "oracle", cache_path=None, llm=None):
        super().__init__(limit)
        self.ablate = frozenset(ablate)
        self._extractor = make_extractor(extractor, cache_path, llm)
        self._done: set[str] = set()
        self._versions: dict[tuple[str, str], list[Version]] = {}
        self._constraints: list[tuple[Entry, str]] = []
        self._fragments: list[tuple[Entry, str]] = []
        self.quarantined: list[tuple[str, str]] = []  # (entry id, fragment)
        self.refusals: list[str] = []  # entry ids whose extraction was refused
        self.last_trace: list[dict] = []

    # ---- writing ----

    def end_session(self, session: int) -> None:
        for e in sorted(self._entries.values(), key=lambda e: e.clock):
            if e.session == session and e.id not in self._done:
                self._done.add(e.id)
                self._ingest(e)

    def _ingest(self, e: Entry) -> None:
        ex = (self._extractor.extract(e, known=self.known_lines(e.text))
              if getattr(self._extractor, "wants_known", False) else self._extractor.extract(e))
        if ex.refused:
            self.refusals.append(e.id)
        trust_on = "trust" not in self.ablate
        if "pinned_constraints" not in self.ablate:
            texts = ex.constraints if trust_on else (ex.constraints or rule_constraints(e, require_trusted=False))
            self._constraints.extend((e, t) for t in texts)
        if e.trust == "untrusted" and e.kind in ("tool_output", "document"):
            if trust_on:
                kept, held = split_untrusted(e.text)
                values = [_norm(f.value) for f in ex.facts]
                # a fragment whose fact was extracted is represented by that fact, not by the raw text
                self._fragments.extend((e, f) for f in kept if not any(v in _norm(f) for v in values))
                self.quarantined.extend((e.id, f) for f in held)
            else:
                self._fragments.append((e, e.text))  # no filter: the text goes in as it is
        for f in ex.facts:
            self._versions.setdefault((f.entity, f.attribute), []).append(
                Version(f, e, f.valid_from, AUTHORITY.get(f.source, 0), TRUST[e.trust]))

    def known_lines(self, text: str, k: int = 8) -> list[str]:
        """Current shared facts most related to `text`, to help the model read relative updates."""
        lines = []
        for key in sorted(self._versions):
            vis = [v for v in self._versions[key] if v.entry.scope != "private"]
            for v in self._resolve(vis) if vis else []:
                lines.append(f"{v.fact.entity} {v.fact.attribute} = {v.fact.value}")
        scores = bm25_scores(text, lines)
        return [l for _, l in sorted(zip(scores, lines), key=lambda p: (-p[0], p[1]))[:k]]

    def drain_llm_calls(self) -> list:
        return self._extractor.drain() if hasattr(self._extractor, "drain") else []

    # ---- reading ----

    def _can_see(self, e: Entry, reader: Reader) -> bool:
        return True if "scopes" in self.ablate else visible_to(e, reader)

    def _resolve(self, versions: list[Version]) -> list[Version]:
        """Current versions of one key from the visible versions, in write order."""
        validity, trust_on = "validity" not in self.ablate, "trust" not in self.ablate
        current: list[Version] = []
        latest = 0
        for v in sorted(versions, key=lambda v: v.entry.clock):
            v = Version(v.fact, v.entry, v.time, v.authority, v.trust)
            if v.time == UNKNOWN_TIME:
                v.time = latest + 1
            key = f"{v.fact.entity}/{v.fact.attribute}"
            same = next((c for c in current if c.fact.value == v.fact.value), None)
            if same is not None:
                if v.trust > same.trust:  # a more trusted source confirms the value
                    current[current.index(same)] = v
            elif not validity or not current:
                current.append(v)
            elif trust_on and v.trust == 0 and current[0].trust > 0:
                self.last_trace.append({"op": "reject", "key": key, "entry_id": v.entry.id,
                                        "reason": "untrusted source cannot override a trusted fact"})
            else:
                c = current[0]
                if v.time > c.time:
                    self._note_resolve(key, v, c, "later_event")
                    current = [v]
                elif v.time < c.time:
                    self.last_trace.append({"op": "reject", "key": key, "entry_id": v.entry.id, "reason": "older event"})
                elif v.authority > c.authority:
                    self._note_resolve(key, v, c, "authority")
                    current = [v]
                elif v.authority < c.authority:
                    self.last_trace.append({"op": "reject", "key": key, "entry_id": v.entry.id, "reason": "lower authority"})
                else:
                    self.last_trace.append({"op": "resolve", "key": key, "winner": None, "loser": None, "rule": "disputed"})
                    current.append(v)
            latest = max(latest, v.time)
        return current

    def _note_resolve(self, key: str, winner: Version, loser: Version, rule: str) -> None:
        self.last_trace.append({"op": "resolve", "key": key, "winner": winner.fact.value, "loser": loser.fact.value,
                                "rule": rule})

    def _fact_items(self, reader: Reader) -> list[tuple[ContextItem, int]]:
        trust_on = "trust" not in self.ablate
        items: list[tuple[ContextItem, int]] = []
        for key in sorted(self._versions):
            visible = [v for v in self._versions[key] if self._can_see(v.entry, reader)]
            if not visible:
                continue
            cur = self._resolve(visible)
            groups = [cur] if len(cur) > 1 and "validity" not in self.ablate else [[v] for v in cur]
            for g in groups:
                f = g[0].fact
                disputed = len(g) > 1
                quoted = trust_on and any(v.entry.trust == "untrusted" for v in g)
                if disputed:
                    body = " | ".join(f"{v.fact.value} (per {v.fact.source})" for v in g)
                    text = f"{f.entity} {f.attribute}: {body} [DISPUTED]"
                else:
                    text = f"{f.entity} {f.attribute}: {f.value}"
                if quoted:
                    text = "[data] " + text
                item = ContextItem(id=f"fact-{f.entity}-{f.attribute}-{g[0].entry.id}", kind="quoted_data" if quoted else "fact",
                                   text=text, entry_ids=tuple(v.entry.id for v in g), disputed=disputed)
                items.append((item, max(v.time for v in g)))
        return items

    def context(self, reader: Reader) -> Context:
        self.last_trace = []
        out: list[ContextItem] = []
        seen: set[str] = set()
        for e, text in self._constraints:
            if self._can_see(e, reader) and text not in seen:
                seen.add(text)
                out.append(ContextItem(id=f"constraint-{e.id}-{len(out)}", kind="constraint", text=text, entry_ids=(e.id,)))
        used = sum(count(i.text) for i in out)
        if used > self.limit:
            raise ValueError(f"pinned constraints need {used} tokens, the limit is {self.limit}")
        for e_id, frag in self.quarantined:
            self.last_trace.append({"op": "quarantine", "entry_id": e_id, "reason": "instruction-like fragment"})

        facts = self._fact_items(reader)
        frags = [(ContextItem(id=f"frag-{e.id}-{n}", kind="raw" if "trust" in self.ablate else "quoted_data", text=t,
                              entry_ids=(e.id,)), e.clock)
                 for n, (e, t) in enumerate(self._fragments) if self._can_see(e, reader)]
        for group in (facts, frags):
            scores = bm25_scores(reader.query, [i.text for i, _ in group])
            ranked = sorted(zip(scores, group), key=lambda p: (-p[0], -p[1][1], p[1][0].id))
            for _, (item, _) in ranked:
                cost = count(item.text)
                if used + cost <= self.limit:
                    out.append(item)
                    used += cost
        return make_context(out)
