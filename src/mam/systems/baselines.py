"""Simple baseline systems: the whole history, a sliding window, and BM25 search over all visible records."""
from __future__ import annotations

from mam.systems.base import MemorySystem, make_context
from mam.systems.ranking import bm25_scores
from mam.tokens import count
from mam.types import Context, ContextItem, Entry, Reader

def _raw(entry: Entry) -> ContextItem:
    """The record as it is, without processing: kind="raw", the text does not change."""
    return ContextItem(id=f"raw-{entry.id}", kind="raw", text=entry.text, entry_ids=(entry.id,))

class FullHistory(MemorySystem):
    """Everything visible, in order. No limit, nothing is cut (an upper bound on completeness, but not on budget)."""

    def context(self, reader: Reader) -> Context:
        return make_context([_raw(e) for e in self._visible(reader)])

class SlidingWindow(MemorySystem):
    """The most recent visible records that fit within the limit, in chronological order."""

    def context(self, reader: Reader) -> Context:
        kept: list[ContextItem] = []
        used = 0
        # Go from new to old and stop at the first one that does not fit:
        # the window must be a continuous piece of history, with no gaps.
        for e in reversed(self._visible(reader)):
            cost = count(e.text)
            if used + cost > self.limit:
                break
            kept.append(_raw(e))
            used += cost
        kept.reverse()  # return to chronological order
        return make_context(kept)

class SharedRagBm25(MemorySystem):
    """BM25 over the visible records; the best matches first, until the limit is filled."""

    def context(self, reader: Reader) -> Context:
        docs = self._visible(reader)
        scores = bm25_scores(reader.query, [d.text for d in docs])
        scored = list(zip(scores, docs))
        # With an equal score the more recent record goes first.
        scored.sort(key=lambda p: (-p[0], -p[1].clock))
        kept, used = [], 0
        for score, d in scored:
            cost = count(d.text)
            # Unlike the window, an oversized record is skipped, not stopped at:
            # a shorter and still relevant one may be found further on.
            if used + cost <= self.limit:
                kept.append(_raw(d))
                used += cost
        return make_context(kept)
