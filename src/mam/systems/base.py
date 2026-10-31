"""Shared behaviour of all memory systems: idempotent writes, scope filter, token accounting."""
from __future__ import annotations

from mam.tokens import count
from mam.types import Context, ContextItem, Entry, Reader


def visible_to(entry: Entry, reader: Reader) -> bool:
    """Scope filter. Applied before any ranking or search."""
    if entry.scope == "private":
        return entry.author == reader.role
    if entry.scope == "task":
        return entry.task_id == reader.task_id
    return True


def make_context(items: list[ContextItem]) -> Context:
    return Context(items=items, token_count=sum(count(i.text) for i in items))


class MemorySystem:
    """Entries arrive in increasing clock order; a repeated entry id is ignored."""

    def __init__(self, limit: int = 2000):
        self.limit = limit
        self._entries: dict[str, Entry] = {}

    def write(self, entry: Entry) -> None:
        if entry.id not in self._entries:
            self._entries[entry.id] = entry

    def end_session(self, session: int) -> None:
        """Hook for systems that extract facts or build summaries at session end."""

    def drain_llm_calls(self) -> list:
        return []

    def context(self, reader: Reader) -> Context:
        raise NotImplementedError

    def _visible(self, reader: Reader) -> list[Entry]:
        return sorted((e for e in self._entries.values() if visible_to(e, reader)), key=lambda e: e.clock)
