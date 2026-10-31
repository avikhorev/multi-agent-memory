"""Scenario types and JSON (de)serialization (spec section 3 and 7)."""
from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from pathlib import Path

from .types import Fact


@dataclass
class ActionPattern:
    tool: str
    args: dict


@dataclass
class Event:
    id: str
    type: str  # user_message | tool_data | note
    text: str
    author: str
    scope: str
    tool: str | None
    args: dict | None
    facts: list[str]
    factor: bool


@dataclass
class Session:
    index: int
    events: list[Event]


@dataclass
class Constraint:
    id: str
    text: str
    introduced_in: int
    event_id: str
    forbidden: list[ActionPattern]


@dataclass
class CheckpointContext:
    present: list[str] = field(default_factory=list)
    absent: list[str] = field(default_factory=list)
    absent_outside_quoted: list[str] = field(default_factory=list)
    disputed_both: list[list[str]] = field(default_factory=list)


@dataclass
class CheckpointAnswer:
    expect: str | None = None
    stale: list[str] = field(default_factory=list)
    disputed: bool = False


@dataclass
class CheckpointAction:
    forbidden: list[ActionPattern] = field(default_factory=list)
    required: list[ActionPattern] = field(default_factory=list)


@dataclass
class Checkpoint:
    id: str
    session: int
    role: str
    task_text: str
    kind: str  # value | constraint | conflict | isolation | injection
    context: CheckpointContext
    answer: CheckpointAnswer
    action: CheckpointAction
    required_events: list[str]
    factor: bool


@dataclass
class Scenario:
    id: str
    category: str
    split: str
    seed: int
    variant: str
    resolution: str
    n_sessions: int
    sessions: list[Session]
    facts: list[Fact]
    constraints: list[Constraint]
    checkpoints: list[Checkpoint]


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
