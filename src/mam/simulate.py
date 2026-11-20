"""Tool simulator and the memory entry stream (section 4 of the specification)."""
from __future__ import annotations

import json

from .scenario import Scenario
from .types import Entry

def _key(tool: str, args: dict) -> tuple[str, str]:
    """Key of the answer lookup: the tool name and the arguments in canonical form
    (sort_keys, so that the order of the arguments does not affect the match)."""
    return (tool, json.dumps(args, sort_keys=True))

class Simulator:
    """Returns the tool_data of the scenario by the pair (tool, arguments); update_record only writes to the action journal.

    Needed so that the agent can "call tools" without real systems: all responses
    are recorded in the scenario in advance, so the run is reproducible.
    """

    def __init__(self, scenario: Scenario):
        # Table of ready answers: take all tool_data events from all sessions.
        self._data = {_key(e.tool, e.args): e.text
                      for sess in scenario.sessions for e in sess.events if e.type == "tool_data"}
        # Journal of modifying calls; it is later used to check what the agent did.
        self.action_log: list[dict] = []

    def call(self, tool: str, args: dict) -> str:
        if tool == "update_record":
            # The record changes nothing in the data, but it is logged for the evaluation of the agent's actions.
            self.action_log.append({"tool": tool, "args": dict(args)})
            return "OK: change recorded"
        text = self._data.get(_key(tool, args))
        if text is None:
            # The agent called something that is not in the scenario: return an error, do not invent data.
            return f"ERROR: no data for {tool} {json.dumps(args, sort_keys=True)}"
        return text

def entries(scenario: Scenario) -> list[Entry]:
    """One Entry record per event in stream order; the clock grows by 1 per record.

    Here it is also decided what to trust (trust) and where the record comes from (source):
    this determines how the memory system will process the record further.
    """
    facts = {f.id: f for f in scenario.facts}
    task_id = f"task-{scenario.id}"
    out: list[Entry] = []
    clock = 0
    for sess in scenario.sessions:
        # Which tool_data event produced this fact (by the fact id) — needed to
        # find the origin of an agent note that restates the tool's output.
        tool_events = {fid: e for e in sess.events if e.type == "tool_data" for fid in e.facts}
        for e in sess.events:
            clock += 1
            origin = None
            if e.type == "user_message":
                # A user message is the most trusted source.
                kind, source, trust = "user_message", "user", "trusted"
            elif e.type == "tool_data":
                # Tool and document data are untrusted: an instruction may be injected into them.
                kind, source, trust = (("document", "document", "untrusted") if e.tool == "read_document"
                                       else ("tool_output", "tool", "untrusted"))
            else:
                # The rest are the agent's own records: a personal draft or a shared note.
                kind = "draft" if e.scope == "private" else "agent_note"
                source, trust = "agent", "agent"
                srcs = [tool_events.get(fid) for fid in e.facts]
                if e.facts and all(srcs) and len({x.id for x in srcs}) == 1:
                    # A note that restates one source entirely inherits its origin
                    # and its distrust, so that the note does not "launder" untrusted data.
                    origin = srcs[0].id
                    source = "document" if srcs[0].tool == "read_document" else "tool"
                    trust = "untrusted"
            out.append(Entry(
                id=e.id, clock=clock, session=sess.index, author=e.author, kind=kind, text=e.text,
                scope=e.scope, source=source, trust=trust, origin=origin, task_id=task_id,
                oracle_facts=tuple(facts[fid] for fid in e.facts)))
    return out
