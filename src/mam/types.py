"""Общие типы (разделы 5 и 8 спецификации)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Fact:
    id: str  # факты сценария: "fa-NNNN" для базовых фактов, "fx-NNNN" для фактов фактора
    entity: str  # о чём факт, например "Atlas/admin"
    attribute: str  # поле, например "handover_date"
    value: str
    valid_from: int  # номер дня, с которого факт начинает действовать; экстракторы могут использовать UNKNOWN_TIME (-1)
    valid_to: int | None  # номер дня, когда факт перестаёт действовать; None — действует до сих пор
    supersedes: str | None  # id факта, который этот факт заменяет
    source: str  # user | tool | document | agent


@dataclass(frozen=True)
class Entry:
    id: str
    clock: int
    session: int
    author: str
    kind: str  # user_message | agent_note | tool_output | document | draft
    text: str
    scope: str  # private | task | shared
    source: str  # user | agent | tool | document
    trust: str  # trusted | agent | untrusted
    origin: str | None
    task_id: str
    oracle_facts: tuple[Fact, ...] = ()


@dataclass(frozen=True)
class Reader:
    role: str
    task_id: str
    session: int
    query: str


@dataclass(frozen=True)
class ContextItem:
    id: str
    kind: str  # constraint | fact | summary | raw | quoted_data
    text: str
    entry_ids: tuple[str, ...] = ()
    disputed: bool = False
    superseded: bool = False


@dataclass
class Context:
    items: list[ContextItem] = field(default_factory=list)
    token_count: int = 0

    def render(self) -> str:
        return "\n".join(item.text for item in self.items)
