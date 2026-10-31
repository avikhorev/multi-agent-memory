"""Simple baselines: full history, sliding window and BM25 retrieval over all visible entries."""
from __future__ import annotations

import math
import re

from mam.systems.base import MemorySystem, make_context
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


_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class SharedRagBm25(MemorySystem):
    """BM25 over visible entries; best matches first until the limit is full."""

    K1, B = 1.5, 0.75

    def context(self, reader: Reader) -> Context:
        docs = self._visible(reader)
        if not docs:
            return make_context([])
        toks = [tokenize(d.text) for d in docs]
        avg = sum(len(t) for t in toks) / len(toks)
        df: dict[str, int] = {}
        for t in toks:
            for w in set(t):
                df[w] = df.get(w, 0) + 1
        query = tokenize(reader.query)
        scored = []
        for d, t in zip(docs, toks):
            tf: dict[str, int] = {}
            for w in t:
                tf[w] = tf.get(w, 0) + 1
            score = 0.0
            for w in set(query):
                if w in tf:
                    idf = math.log(1 + (len(docs) - df[w] + 0.5) / (df[w] + 0.5))
                    score += idf * tf[w] * (self.K1 + 1) / (tf[w] + self.K1 * (1 - self.B + self.B * len(t) / avg))
            scored.append((score, d))
        scored.sort(key=lambda p: (-p[0], -p[1].clock))
        kept, used = [], 0
        for score, d in scored:
            cost = count(d.text)
            if used + cost <= self.limit:
                kept.append(_raw(d))
                used += cost
        return make_context(kept)
