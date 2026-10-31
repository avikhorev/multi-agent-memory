"""Tool simulator and the feed of memory entries (spec section 4)."""
from __future__ import annotations

import json

from .scenario import Scenario
from .types import Entry


def _key(tool: str, args: dict) -> tuple[str, str]:
    return (tool, json.dumps(args, sort_keys=True))


class Simulator:
    """Returns the scenario's tool_data by (tool, args); update_record only goes to the action log."""

    def __init__(self, scenario: Scenario):
        self._data = {_key(e.tool, e.args): e.text
                      for sess in scenario.sessions for e in sess.events if e.type == "tool_data"}
        self.action_log: list[dict] = []

    def call(self, tool: str, args: dict) -> str:
        if tool == "update_record":
            self.action_log.append({"tool": tool, "args": dict(args)})
            return "OK: change recorded"
        text = self._data.get(_key(tool, args))
        if text is None:
            return f"ERROR: no data for {tool} {json.dumps(args, sort_keys=True)}"
        return text


def entries(scenario: Scenario) -> list[Entry]:
    """One Entry per event in feed order; clock grows by 1 per entry."""
    facts = {f.id: f for f in scenario.facts}
    task_id = f"task-{scenario.id}"
    out: list[Entry] = []
    clock = 0
    for sess in scenario.sessions:
        tool_events = {fid: e for e in sess.events if e.type == "tool_data" for fid in e.facts}
        for e in sess.events:
            clock += 1
            origin = None
            if e.type == "user_message":
                kind, source, trust = "user_message", "user", "trusted"
            elif e.type == "tool_data":
                kind, source, trust = (("document", "document", "untrusted") if e.tool == "read_document"
                                       else ("tool_output", "tool", "untrusted"))
            else:
                kind = "draft" if e.scope == "private" else "agent_note"
                source, trust = "agent", "agent"
                srcs = [tool_events.get(fid) for fid in e.facts]
                if e.facts and all(srcs) and len({x.id for x in srcs}) == 1:
                    origin = srcs[0].id
                    source = "document" if srcs[0].tool == "read_document" else "tool"
                    trust = "untrusted"
            out.append(Entry(
                id=e.id, clock=clock, session=sess.index, author=e.author, kind=kind, text=e.text,
                scope=e.scope, source=source, trust=trust, origin=origin, task_id=task_id,
                oracle_facts=tuple(facts[fid] for fid in e.facts)))
    return out
