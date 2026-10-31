"""Simple baselines: full history, sliding window and BM25 retrieval over all visible entries."""
from __future__ import annotations

from mam.systems.base import MemorySystem, make_context
from mam.systems.ranking import bm25_scores
from mam.tokens import count
from mam.types import Context, ContextItem, Entry, Reader


def _raw(entry: Entry) -> ContextItem:
    return ContextItem(id=f"raw-{entry.id}", kind="raw", text=entry.text, entry_ids=(entry.id,))


class FullHistory(MemorySystem):
    """Everything visible, in order. There is no limit and nothing is ever truncated."""

    def context(self, reader: Reader) -> Context:
        return make_context([_raw(e) for e in self._visible(reader)])


class SlidingWindow(MemorySystem):
    """The most recent visible entries that fit the limit, in chronological order."""

    def context(self, reader: Reader) -> Context:
        kept: list[ContextItem] = []
        used = 0
        for e in reversed(self._visible(reader)):
            cost = count(e.text)
            if used + cost > self.limit:
                break
            kept.append(_raw(e))
            used += cost
        kept.reverse()
        return make_context(kept)


class SharedRagBm25(MemorySystem):
    """BM25 over visible entries; best matches first until the limit is full."""

    def context(self, reader: Reader) -> Context:
        docs = self._visible(reader)
        scores = bm25_scores(reader.query, [d.text for d in docs])
        scored = list(zip(scores, docs))
        scored.sort(key=lambda p: (-p[0], -p[1].clock))
        kept, used = [], 0
        for score, d in scored:
            cost = count(d.text)
            if used + cost <= self.limit:
                kept.append(_raw(d))
                used += cost
        return make_context(kept)
