"""Scenario types and (de)serialization to JSON (sections 3 and 7 of the specification).

A scenario is a reproducible history of the work of several agents (sessions and events),
a key of correct answers (facts) and checkpoints at which the memory is checked.
"""
from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from pathlib import Path

from .types import Fact


@dataclass
class ActionPattern:
    """Action template of an agent: matches if the tool is the same and the arguments contain the given values."""
    tool: str  # tool name: read_document | read_status | update_record
    args: dict  # values that must be in the call's arguments, e.g. {"field": "atlas.budget_usd"}


@dataclass
class Event:
    """One event of the history: a user utterance, a tool response or an agent note."""
    id: str  # unique: "e-NNNN" for base events, "x-NNNN" for factor events
    type: str  # user_message | tool_data | note
    text: str  # what the event says; for tool_data — the text the tool returned
    author: str  # user | planner | worker | reviewer | tool
    scope: str  # task | shared | private; private is a draft that only its author sees
    tool: str | None  # only for tool_data: read_document | read_status; otherwise None
    args: dict | None  # only for tool_data: the arguments of this call, e.g. {"doc_id": "D-12"}
    facts: list[str]  # ids of reference facts (oracle) that the event reports; the key for the extractor and for evaluation
    factor: bool  # True if the event was added by the category's factor


@dataclass
class Session:
    """A group of events of one work session; agents have no memory of their own between sessions."""
    index: int  # session number, from 1
    events: list[Event]  # in the order in which the memory receives them


@dataclass
class Constraint:
    """A standing user constraint ("never do X"); checked in category C2."""
    id: str  # e.g. "k-0001"
    text: str  # the user's wording of the constraint
    introduced_in: int  # number of the session in which the user names it
    event_id: str  # id of the user_message event in which it is named
    forbidden: list[ActionPattern]  # actions that would violate the constraint


@dataclass
class CheckpointContext:
    """Requirements on the memory context (context level): what it must and must not contain."""
    present: list[str] = field(default_factory=list)  # must be in the assembled context
    absent: list[str] = field(default_factory=list)  # must not appear anywhere in the context
    absent_outside_quoted: list[str] = field(default_factory=list)  # allowed only inside quoted_data items
    disputed_both: list[list[str]] = field(default_factory=list)  # pairs of values: both must be in the context and marked disputed


@dataclass
class CheckpointAnswer:
    """Requirements on the agent's answer (action level)."""
    expect: str | None = None  # expected answer (for evaluation only); None if no value is expected
    stale: list[str] = field(default_factory=list)  # replaced values that must not be in the answer
    disputed: bool = False  # True if the answer must contain DISPUTED


@dataclass
class CheckpointAction:
    """Requirements on the agent's actions with tools."""
    forbidden: list[ActionPattern] = field(default_factory=list)  # actions that must not occur (evaluation only)
    required: list[ActionPattern] = field(default_factory=list)  # actions that must occur (evaluation only)


@dataclass
class Checkpoint:
    """Checkpoint: a question to the agent at a given moment and the key for its automatic check."""
    id: str  # "cp-N" for base checkpoints, "cpx-N" for factor checkpoints
    session: int  # number of the session in which the question is asked
    role: str  # planner | worker | reviewer: whose memory context is checked
    task_text: str  # the question the agent receives; the fields below are not shown to it
    kind: str  # what is checked: value | constraint | conflict | isolation | injection
    context: CheckpointContext  # what the memory context must or must not contain
    answer: CheckpointAnswer  # expected answer (evaluation only)
    action: CheckpointAction  # expected and forbidden actions (evaluation only)
    required_events: list[str]  # ids of events that carry the answer; any one of them is enough
    factor: bool  # True if the checkpoint was added by the category's factor


@dataclass
class Scenario:
    """One benchmark scenario. Full format: docs/SCENARIO_FORMAT.md, section 3."""
    id: str  # unique: "<category>-<split>-<number>", e.g. "C3-eval-0000"
    category: str  # C0 control, C1 update, C2 constraint, C3 conflict, C4 isolation, C5 injection, C6 long history
    split: str  # dev (tuning), eval (main results), holdout (hard cases)
    seed: int  # generator seed; together with category, variant and n_sessions it determines the file byte for byte
    variant: str  # C1 and C3: explicit | implicit; otherwise none
    resolution: str  # only C3: later_event | authority | disputed; otherwise none
    n_sessions: int  # 10 in C0–C5; 10, 20 or 30 in C6
    sessions: list[Session]  # the history passed to the memory, in this order
    facts: list[Fact]  # the key of answers: all true facts of the world, including replaced ones
    constraints: list[Constraint]  # user constraints (C2)
    checkpoints: list[Checkpoint]  # questions with their answer keys


def to_dict(scenario: Scenario) -> dict:
    """The scenario as a plain dict (nested dataclasses are unfolded recursively)."""
    return dataclasses.asdict(scenario)


def _patterns(items: list[dict]) -> list[ActionPattern]:
    """List of dicts from JSON -> list of ActionPattern."""
    return [ActionPattern(**p) for p in items]


def from_dict(d: dict) -> Scenario:
    """The inverse of to_dict: nested structures are assembled by hand, because Event(**e) and the like do not create them themselves."""
    sessions = [Session(index=s["index"], events=[Event(**e) for e in s["events"]]) for s in d["sessions"]]
    constraints = [
        Constraint(id=c["id"], text=c["text"], introduced_in=c["introduced_in"], event_id=c["event_id"],
                   forbidden=_patterns(c["forbidden"]))
        for c in d["constraints"]
    ]
    checkpoints = []
    for c in d["checkpoints"]:
        checkpoints.append(Checkpoint(
            id=c["id"], session=c["session"], role=c["role"], task_text=c["task_text"], kind=c["kind"],
            context=CheckpointContext(**c["context"]),
            answer=CheckpointAnswer(**c["answer"]),
            action=CheckpointAction(forbidden=_patterns(c["action"]["forbidden"]),
                                    required=_patterns(c["action"]["required"])),
            required_events=c["required_events"], factor=c["factor"]))
    return Scenario(
        id=d["id"], category=d["category"], split=d["split"], seed=d["seed"], variant=d["variant"],
        resolution=d["resolution"], n_sessions=d["n_sessions"], sessions=sessions,
        facts=[Fact(**f) for f in d["facts"]], constraints=constraints, checkpoints=checkpoints)


def dumps(scenario: Scenario) -> str:
    """JSON text of the scenario. sort_keys and a fixed indent give the same result on every run
    (byte-for-byte reproducibility is needed); ensure_ascii=False keeps non-ASCII text readable."""
    return json.dumps(to_dict(scenario), sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def loads(text: str) -> Scenario:
    return from_dict(json.loads(text))


def dump(scenario: Scenario, path) -> None:
    """We write bytes so that line breaks do not depend on the OS."""
    Path(path).write_bytes(dumps(scenario).encode("utf-8"))


def load(path) -> Scenario:
    return loads(Path(path).read_text(encoding="utf-8"))
