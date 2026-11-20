"""Common behavior of all memory systems: idempotent write, scope filter, token counting."""
from __future__ import annotations

from mam.tokens import count
from mam.types import Context, ContextItem, Entry, Reader

def visible_to(entry: Entry, reader: Reader) -> bool:
    """Scope filter. It is applied before any ranking and search,
    so that a closed record cannot get into the context of another agent."""
    if entry.scope == "private":
        # A personal record is seen only by its author (by role).
        return entry.author == reader.role
    if entry.scope == "task":
        # A task record is visible only within the same task.
        return entry.task_id == reader.task_id
    # The other scopes (shared) are visible to everyone.
    return True

def make_context(items: list[ContextItem]) -> Context:
    """Assembles the context and counts its size in tokens."""
    return Context(items=items, token_count=sum(count(i.text) for i in items))

class MemorySystem:
    """Base class. Records arrive in ascending clock order; a repeated record id is ignored."""

    def __init__(self, limit: int = 2000):
        # The context budget in tokens: the system returns no more than this.
        self.limit = limit
        # All accepted records by id; a repeat does not overwrite (the record is idempotent).
        self._entries: dict[str, Entry] = {}

    def write(self, entry: Entry) -> None:
        if entry.id not in self._entries:
            self._entries[entry.id] = entry

    def end_session(self, session: int) -> None:
        """Hook for systems that extract facts or build summaries at the end of a session."""

    def drain_llm_calls(self) -> list:
        """Returns the accumulated model calls for cost accounting; systems without a model have none."""
        return []

    def drain_extractions(self) -> list[dict]:
        """Returns the accumulated extraction results (for the cache); systems without extraction return nothing."""
        return []

    def context(self, reader: Reader) -> Context:
        """Main method: what to show the reader. Implemented in each system."""
        raise NotImplementedError

    def _visible(self, reader: Reader) -> list[Entry]:
        """Records visible to the reader, in chronological order."""
        return sorted((e for e in self._entries.values() if visible_to(e, reader)), key=lambda e: e.clock)
