"""Scenario types and JSON (de)serialization (spec section 3 and 7)."""
from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from pathlib import Path

from .types import Fact


@dataclass
class ActionPattern:
    tool: str  # read_document | read_status | update_record
    args: dict  # values that must appear in the call's args, e.g. {"field": "atlas.budget_usd"}


@dataclass
class Event:
    id: str  # unique: "e-NNNN" for base events, "x-NNNN" for factor events
    type: str  # user_message | tool_data | note
    text: str  # what the event says; for tool_data, the text the tool returns
    author: str  # user | planner | worker | reviewer | tool
    scope: str  # task | shared | private; private is a draft seen only by its author
    tool: str | None  # tool_data only: read_document | read_status; otherwise None
    args: dict | None  # tool_data only: arguments of that call, e.g. {"doc_id": "D-12"}
    facts: list[str]  # ids of ORACLE facts this event reports (answer key)
    factor: bool  # True if the category factor added this event


@dataclass
class Session:
    index: int  # session number, 1-based
    events: list[Event]  # in the order the memory receives them


@dataclass
class Constraint:
    id: str  # e.g. "k-0001"
    text: str  # the user's wording of the constraint
    introduced_in: int  # session number where the user states it
    event_id: str  # id of the user_message event that states it
    forbidden: list[ActionPattern]  # actions that would break the constraint


@dataclass
class CheckpointContext:
    present: list[str] = field(default_factory=list)  # must appear in the assembled context
    absent: list[str] = field(default_factory=list)  # must appear nowhere in the context
    absent_outside_quoted: list[str] = field(default_factory=list)  # allowed only inside quoted_data items
    disputed_both: list[list[str]] = field(default_factory=list)  # value pairs that must both appear, marked disputed


@dataclass
class CheckpointAnswer:
    expect: str | None = None  # expected answer (scoring only); None when no value is expected
    stale: list[str] = field(default_factory=list)  # superseded values that must not appear in the answer
    disputed: bool = False  # True if the answer must say DISPUTED


@dataclass
class CheckpointAction:
    forbidden: list[ActionPattern] = field(default_factory=list)  # actions that must not occur (scoring only)
    required: list[ActionPattern] = field(default_factory=list)  # actions that must occur (scoring only)


@dataclass
class Checkpoint:
    id: str  # "cp-N" for base checkpoints, "cpx-N" for factor checkpoints
    session: int  # session number at which the question is asked
    role: str  # planner | worker | reviewer: whose memory context is checked
    task_text: str  # the question given to the agent; the fields below are not shown to it
    kind: str  # what is checked: value | constraint | conflict | isolation | injection
    context: CheckpointContext  # what the memory context must or must not contain
    answer: CheckpointAnswer  # expected answer (scoring only)
    action: CheckpointAction  # expected and forbidden actions (scoring only)
    required_events: list[str]  # ids of events that hold the answer; any one of them is enough
    factor: bool  # True if the category factor added this checkpoint


@dataclass
class Scenario:
    """One benchmark scenario. Full format: docs/SCENARIO_FORMAT.md, section 3."""
    id: str  # unique: "<category>-<split>-<number>", e.g. "C3-eval-0000"
    category: str  # C0 control, C1 update, C2 constraint, C3 conflict, C4 isolation, C5 injection, C6 long history
    split: str  # dev (tuning), eval (main results), holdout (hard cases)
    seed: int  # generator seed; with category, variant and n_sessions it fixes the file byte for byte
    variant: str  # C1 and C3: explicit | implicit; none otherwise
    resolution: str  # C3 only: later_event | authority | disputed; none otherwise
    n_sessions: int  # 10 in C0 to C5; 10, 20 or 30 in C6
    sessions: list[Session]  # history, given to the memory in this order
    facts: list[Fact]  # answer key: all true facts of the world, including replaced ones
    constraints: list[Constraint]  # user constraints (C2)
    checkpoints: list[Checkpoint]  # questions with their answer keys


def to_dict(scenario: Scenario) -> dict:
    return dataclasses.asdict(scenario)


def _patterns(items: list[dict]) -> list[ActionPattern]:
    return [ActionPattern(**p) for p in items]


def from_dict(d: dict) -> Scenario:
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
    return json.dumps(to_dict(scenario), sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def loads(text: str) -> Scenario:
    return from_dict(json.loads(text))


def dump(scenario: Scenario, path) -> None:
    Path(path).write_bytes(dumps(scenario).encode("utf-8"))


def load(path) -> Scenario:
    return loads(Path(path).read_text(encoding="utf-8"))
