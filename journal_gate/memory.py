"""Journal memory: ours3 on an append-only journal, with filler prefixes and trust that does not depend on write order.

The entries are the journal. Facts, constraints, fragments and quarantine are derived and can be rebuilt from it
without a model call, because the result of each extraction is kept by entry id.
"""
from dataclasses import replace

from mam.extract import UNKNOWN_TIME
from post_hoc_ours2 import Ours3


class _Memo:
    """Extractor wrapper: the first result for an entry id is kept and returned for every later call."""

    def __init__(self, inner, store):
        self._inner = inner
        self.store = store

    def extract(self, entry, known=()):
        if entry.id not in self.store:
            self.store[entry.id] = (self._inner.extract(entry, known=known)
                                    if getattr(self._inner, "wants_known", False) else self._inner.extract(entry))
        return self.store[entry.id]

    def __getattr__(self, name):  # wants_known, drain, drain_log, parse_errors
        return getattr(self._inner, name)


class Journal(Ours3):
    def __init__(self, limit, **kw):
        super().__init__(limit, **kw)
        self._extractions = {}
        self._extractor = _Memo(self._extractor, self._extractions)

    def rebuild(self):
        """Clear the derived stores and replay the ingest over the journal in clock order, with no model call."""
        self._versions, self._constraints, self._fragments = {}, [], []
        self.quarantined, self.refusals = [], []
        for e in sorted(self._entries.values(), key=lambda e: e.clock):
            if e.id in self._done:
                self._ingest(e)

    def user_messages(self):
        """(session, text) of every user message, in clock order."""
        return [(e.session, e.text) for e in sorted(self._entries.values(), key=lambda e: e.clock)
                if e.kind == "user_message"]

    def _filler(self, reader):
        out = []
        for item in super()._filler(reader):
            e = self._entries[item.entry_ids[0]]
            out.append(replace(item, text=f"[s{e.session} {e.author}] {item.text}"))
        return out

    def _resolve(self, versions):
        trusted = [v for v in versions if v.trust > 0]
        if not trusted:
            return super()._resolve(versions)
        cur = super()._resolve(trusted)
        for v in sorted((v for v in versions if v.trust == 0), key=lambda v: v.entry.clock):
            if any(c.fact.value == v.fact.value for c in cur):
                continue
            if v.time == UNKNOWN_TIME or v.time > cur[0].time:
                cur.append(v)
            else:
                self.last_trace.append({"op": "reject", "key": f"{v.fact.entity}/{v.fact.attribute}",
                                        "entry_id": v.entry.id,
                                        "reason": "untrusted source cannot override a trusted fact"})
        return cur
