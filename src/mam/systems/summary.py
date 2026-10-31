"""Rolling summary: one digest line per session, oldest lines dropped to fit the limit."""
from __future__ import annotations

from mam.extract import make_extractor
from mam.systems.base import MemorySystem, make_context
from mam.tokens import count
from mam.types import Context, ContextItem, Reader


class RollingSummary(MemorySystem):
    """Facts found by the extractor, written as short lines and never revised or closed."""

    def __init__(self, limit: int, extractor: str, cache_path=None):
        if extractor == "oracle":
            raise ValueError("rolling_summary has no oracle extractor")
        super().__init__(limit)
        self._extractor = make_extractor(extractor, cache_path)
        self._digests: dict[int, list[str]] = {}
        self._done: set[str] = set()

    def end_session(self, session: int) -> None:
        for e in sorted(self._entries.values(), key=lambda e: e.clock):
            if e.session != session or e.id in self._done or e.scope == "private":
                continue
            self._done.add(e.id)
            lines = self._digests.setdefault(session, [])
            for f in self._extractor.extract(e).facts:
                line = f"{f.entity} {f.attribute}={f.value}"
                if line not in lines:
                    lines.append(line)

    def context(self, reader: Reader) -> Context:
        lines = [f"S{s}: " + "; ".join(ls) for s, ls in sorted(self._digests.items()) if ls]
        while lines and count("\n".join(lines)) > self.limit:
            lines.pop(0)
        if not lines:
            return make_context([])
        return make_context([ContextItem(id="summary", kind="summary", text="\n".join(lines))])
