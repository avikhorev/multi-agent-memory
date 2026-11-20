"""Common types (sections 5 and 8 of the specification): fact, memory entry, reader, item and context."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Fact:
    """An atomic statement about the world: "entity E's field A has value V in the period [from, to)".
    The pair (entity, attribute) is the key by which different versions of one fact are compared."""
    id: str  # scenario facts: "fa-NNNN" for base facts, "fx-NNNN" for factor facts
    entity: str  # what the fact is about, e.g. "Atlas/admin"
    attribute: str  # the field, e.g. "handover_date"
    value: str  # the field's value as a string
    valid_from: int  # day number from which the fact takes effect; extractors may use UNKNOWN_TIME (-1) if the time is unknown
    valid_to: int | None  # day number when the fact stops taking effect; None — in effect until now
    supersedes: str | None  # id of the fact that this fact replaces (an update); None for the first version
    source: str  # who reported it: user | tool | document | agent (the authority depends on it)


@dataclass(frozen=True)
class Entry:
    """One entry arriving into memory: a message, a note, a tool output, etc.
    Immutable (frozen), so that an entry cannot be substituted after the memory has accepted it."""
    id: str  # unique entry id (matches the scenario event id); entries are written idempotently by it
    clock: int  # logical clock: arrival order, grows by 1 with each entry
    session: int  # number of the session in which the entry appeared
    author: str  # author role: user | planner | worker | reviewer | tool; needed for privacy
    kind: str  # kind of entry: user_message | agent_note | tool_output | document | draft
    text: str  # the entry's original text
    scope: str  # visibility: private (author only) | task (within the task) | shared (everyone)
    source: str  # where the content comes from: user | agent | tool | document
    trust: str  # level of trust: trusted | agent | untrusted (untrusted text is data, not commands)
    origin: str | None  # id of the original entry, if this is a restatement of an untrusted source; otherwise None
    task_id: str  # task to which the entry belongs (for the task scope)
    oracle_facts: tuple[Fact, ...] = ()  # reference facts of the entry from the scenario; used by the "oracle" extractor and for evaluation


@dataclass(frozen=True)
class Reader:
    """Who asks the memory for context, and with what question."""
    role: str  # reader's role: planner | worker | reviewer (determines which personal entries they see)
    task_id: str  # current task (determines which task-scope entries are visible)
    session: int  # number of the current session
    query: str  # question/task by which the entries are ranked


@dataclass(frozen=True)
class ContextItem:
    """One piece of the ready context that the agent will see."""
    id: str  # item id, e.g. "raw-e-0003"
    kind: str  # constraint (standing rule) | fact | summary | raw (entry as is) | quoted_data (untrusted, in quotes)
    text: str  # the text that will go into the prompt
    entry_ids: tuple[str, ...] = ()  # entries from which the item was obtained (for tracing)
    disputed: bool = False  # True if two sources of equal strength contradict each other
    superseded: bool = False  # True if the value has already been replaced by a newer one


@dataclass
class Context:
    """Result of the memory's work: items and their total size in tokens."""
    items: list[ContextItem] = field(default_factory=list)  # items in the order the agent will see them
    token_count: int = 0  # sum of the item tokens; must not exceed the system's budget

    def render(self) -> str:
        """Joins the item texts into one block for the prompt."""
        return "\n".join(item.text for item in self.items)
