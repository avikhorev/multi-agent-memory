"""Structured memory: facts with dates, scopes, conflict rules, quarantine and pinned constraints.

Facts are extracted once per session. When reading, the versions visible to the reader are resolved
by key (entity, attribute) in write order. Old versions are not deleted; the decision
is made only at read time, so that scopes, validity and trust can be turned off one at a time
for ablations (measuring the contribution of each mechanism).
"""
from __future__ import annotations

from dataclasses import dataclass

from mam.extract import UNKNOWN_TIME, make_extractor, rule_constraints
from mam.guard import split_untrusted
from mam.systems.base import MemorySystem, make_context, visible_to
from mam.systems.ranking import bm25_scores
from mam.tokens import count
from mam.types import Context, ContextItem, Entry, Fact, Reader

# Authority of a fact's source: with equal time the higher one wins. The user outranks a tool,
# a tool outranks a document, a document outranks an agent note.
AUTHORITY = {"user": 3, "tool": 2, "document": 1, "agent": 0}
# Trust in an entry as a carrier of commands: untrusted (0) cannot override trusted.
TRUST = {"trusted": 2, "agent": 1, "untrusted": 0}


def _norm(text: str) -> str:
    """Form of the text used for substring comparison: lowercased, without spaces and commas (thousands separators)."""
    return "".join(text.lower().replace(",", "").split())


@dataclass
class Version:
    """One version of a fact together with where it came from. Needed to resolve conflicts."""
    fact: Fact  # the fact itself
    entry: Entry  # the entry the fact was extracted from (scope, trust, write order)
    time: int  # time of the event (day); UNKNOWN_TIME (-1) if the text does not name it
    authority: int  # authority of the source per the AUTHORITY table
    trust: int  # trust in the entry per the TRUST table


class Ours(MemorySystem):
    """Our memory system. Entries accumulate; at the end of a session facts are extracted from them,
    and when reading, the context is assembled from constraints, resolved facts and safe fragments."""

    def __init__(self, limit: int, ablate=frozenset(), extractor: str = "oracle", cache_path=None, llm=None):
        super().__init__(limit)
        self.ablate = frozenset(ablate)  # which mechanisms are disabled (validity | scopes | trust | pinned_constraints)
        self._extractor = make_extractor(extractor, cache_path, llm)
        self._done: set[str] = set()  # ids of entries already processed by the extractor (not extracted again)
        # All versions of each fact by key (entity, attribute); rejected ones are kept too, the decision is made at read time.
        self._versions: dict[tuple[str, str], list[Version]] = {}
        self._constraints: list[tuple[Entry, str]] = []  # pinned constraints: (entry, text); not versioned
        self._fragments: list[tuple[Entry, str]] = []  # safe pieces of untrusted texts that did not become facts
        self.quarantined: list[tuple[str, str]] = []  # (entry id, fragment) held back by the quarantine
        self.refusals: list[str] = []  # ids of entries whose extraction the model refused to do
        self.last_trace: list[dict] = []  # trace of the last context(): quarantine / resolve / reject, for explainability

    # ---- write ----

    def end_session(self, session: int) -> None:
        """Extracts facts from the entries of the finished session (in clock order)."""
        for e in sorted(self._entries.values(), key=lambda e: e.clock):
            if e.session == session and e.id not in self._done:
                self._done.add(e.id)
                self._ingest(e)

    def _ingest(self, e: Entry) -> None:
        """Processes one entry: extracts facts and constraints, passes untrusted text through the quarantine."""
        # We give the model extractor the facts already known, so that it understands relative updates
        # ("cut by 25 percent"); the others do not need hints.
        ex = (self._extractor.extract(e, known=self.known_lines(e.text))
              if getattr(self._extractor, "wants_known", False) else self._extractor.extract(e))
        if ex.refused:
            self.refusals.append(e.id)
        trust_on = "trust" not in self.ablate
        if "pinned_constraints" not in self.ablate:
            # Without the trust filter, constraints are also taken from untrusted entries: this measures the harm of having no filter.
            texts = ex.constraints if trust_on else (ex.constraints or rule_constraints(e, require_trusted=False))
            self._constraints.extend((e, t) for t in texts)
        # Untrusted text is data, not commands: pass it through the quarantine.
        if e.trust == "untrusted" and e.kind in ("tool_output", "document"):
            if trust_on:
                kept, held = split_untrusted(e.text)
                values = [_norm(f.value) for f in ex.facts]
                # a fragment from which a fact is already extracted is represented by that fact, not by raw text (no duplicates)
                self._fragments.extend((e, f) for f in kept if not any(v in _norm(f) for v in values))
                self.quarantined.extend((e.id, f) for f in held)
            else:
                self._fragments.append((e, e.text))  # without the filter: the text goes through as is
        # Each fact is a new version under its own key; old ones are not erased.
        for f in ex.facts:
            self._versions.setdefault((f.entity, f.attribute), []).append(
                Version(f, e, f.valid_from, AUTHORITY.get(f.source, 0), TRUST[e.trust]))

    def known_lines(self, text: str, k: int = 8) -> list[str]:
        """Current shared facts closest to `text` (up to k of them) — a hint for the model to read relative updates.
        Private versions are not taken: the hint must not reveal someone else's data."""
        lines = []
        for key in sorted(self._versions):
            vis = [v for v in self._versions[key] if v.entry.scope != "private"]
            for v in self._resolve(vis) if vis else []:
                lines.append(f"{v.fact.entity} {v.fact.attribute} = {v.fact.value}")
        scores = bm25_scores(text, lines)
        return [l for _, l in sorted(zip(scores, lines), key=lambda p: (-p[0], p[1]))[:k]]

    def drain_llm_calls(self) -> list:
        """Model calls made by the extractor (if it makes them) — for cost accounting."""
        return self._extractor.drain() if hasattr(self._extractor, "drain") else []

    def drain_extractions(self) -> list[dict]:
        """Journal of extractions (for saving to the cache)."""
        return self._extractor.drain_log() if hasattr(self._extractor, "drain_log") else []

    # ---- read ----

    def _can_see(self, e: Entry, reader: Reader) -> bool:
        """Whether the entry is visible to the reader; with the scopes ablation everything is visible."""
        return True if "scopes" in self.ablate else visible_to(e, reader)

    def _resolve(self, versions: list[Version]) -> list[Version]:
        """Current versions of one key among the visible versions, in write order.

        Rules when a new version v arrives while c is current:
        - same value: keep the more trusted one (confirmation);
        - validity ablation or no current version: just add it (there may be several versions);
        - untrusted against trusted: reject (untrusted text does not rewrite facts);
        - otherwise: the later event wins; with equal time, the higher authority;
          with equal authority, a dispute (both versions are kept and marked DISPUTED).
        The result is a list; more than one element means a dispute."""
        validity, trust_on = "validity" not in self.ablate, "trust" not in self.ablate
        current: list[Version] = []
        latest = 0
        for v in sorted(versions, key=lambda v: v.entry.clock):
            v = Version(v.fact, v.entry, v.time, v.authority, v.trust)  # a copy: the original version is not changed
            if v.time == UNKNOWN_TIME:
                v.time = latest + 1  # time not named: treat the event as later than everything seen so far
            key = f"{v.fact.entity}/{v.fact.attribute}"  # for the trace
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
        """Trace record of which version won and by which rule."""
        self.last_trace.append({"op": "resolve", "key": key, "winner": winner.fact.value, "loser": loser.fact.value,
                                "rule": rule})

    def _fact_items(self, reader: Reader) -> list[tuple[ContextItem, int]]:
        """Resolved facts as context items; each comes with its time (for ordering at equal relevance)."""
        trust_on = "trust" not in self.ablate
        items: list[tuple[ContextItem, int]] = []
        for key in sorted(self._versions):
            visible = [v for v in self._versions[key] if self._can_see(v.entry, reader)]
            if not visible:
                continue
            cur = self._resolve(visible)
            # A dispute (several versions) is shown as one item; with the validity ablation each version goes separately.
            groups = [cur] if len(cur) > 1 and "validity" not in self.ablate else [[v] for v in cur]
            for g in groups:
                f = g[0].fact
                disputed = len(g) > 1
                # A fact from an untrusted source is given as quoted data marked [data].
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
        """Assembles the context in order of importance: constraints (always), then facts and fragments by relevance into the remaining budget."""
        self.last_trace = []
        out: list[ContextItem] = []
        seen: set[str] = set()
        # Constraints come first and are not cut: skipping a user's rule is more dangerous than skipping a fact.
        for e, text in self._constraints:
            if self._can_see(e, reader) and text not in seen:
                seen.add(text)
                out.append(ContextItem(id=f"constraint-{e.id}-{len(out)}", kind="constraint", text=text, entry_ids=(e.id,)))
        used = sum(count(i.text) for i in out)
        if used > self.limit:  # constraints do not fit — a configuration error; they cannot be silently cut
            raise ValueError(f"pinned constraints need {used} tokens, the limit is {self.limit}")
        # Mark in the trace all held-back fragments (they show that the quarantine worked).
        for e_id, frag in self.quarantined:
            self.last_trace.append({"op": "quarantine", "entry_id": e_id, "reason": "instruction-like fragment"})

        facts = self._fact_items(reader)
        frags = [(ContextItem(id=f"frag-{e.id}-{n}", kind="raw" if "trust" in self.ablate else "quoted_data", text=t,
                              entry_ids=(e.id,)), e.clock)
                 for n, (e, t) in enumerate(self._fragments) if self._can_see(e, reader)]
        # Facts come before raw fragments, so they are taken first; each group is ranked by BM25,
        # and at equal score the fresher one wins; an item that does not fit the budget is skipped.
        for group in (facts, frags):
            scores = bm25_scores(reader.query, [i.text for i, _ in group])
            ranked = sorted(zip(scores, group), key=lambda p: (-p[0], -p[1][1], p[1][0].id))
            for _, (item, _) in ranked:
                cost = count(item.text)
                if used + cost <= self.limit:
                    out.append(item)
                    used += cost
        return make_context(out)
