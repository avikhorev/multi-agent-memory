"""One live unit: a scenario played by model agents against one memory system.

Per session: the user's messages are written, then Planner, Worker (two calls: choose the action, then report)
and Reviewer run in turn, each on a context built from memory only. Notes the agents return are written back.
Scripted conflict notes and private drafts (factor notes of the scenario) are written by the harness, because
agents would not produce them by themselves; ordinary scripted notes are not written in a live run.
"""
from __future__ import annotations

import dataclasses
import json
import time

from mam.agents import AgentResult, run_agent
from mam.llm import LLMClient
from mam.scoring import label_failure, score_action, score_context
from mam.simulate import Simulator, entries
from mam.systems import create
from mam.types import Entry, Reader

GENERIC_PLANNER_TASK = "Decide what the Worker should do next, based on the user's message and the memory."
FALLBACK_WORKER_TASK = "Continue the project work."


def _call_record(role: str, session: int, out) -> dict:
    u = out.usage
    return {"role": role, "session": session, "input_tokens": u.input_tokens,
            "cache_creation_tokens": u.cache_creation_tokens, "cache_read_tokens": u.cache_read_tokens,
            "output_tokens": u.output_tokens, "thinking_tokens": u.thinking_tokens, "cost_usd": u.cost_usd,
            "latency_s": round(out.latency_s, 3), "refusal": out.refusal}


def session_source(scenario, session: int):
    """The one data source offered to the Worker in a session: the factor source if any, else the first."""
    evs = [e for e in scenario.sessions[session - 1].events if e.type == "tool_data"]
    return next((e for e in evs if e.factor), evs[0] if evs else None)


def _source_line(ev) -> str:
    return f"tool: {ev.tool}, args: {json.dumps(ev.args, sort_keys=True)} (about: {ev.text.split(chr(10))[0][:60]})"


def run_live(scenario, cfg: str, llm: LLMClient, *, repeat: int = 0, limit: int = 2000) -> dict:
    system = (create(cfg, limit=limit, extractor="llm", llm=llm) if cfg in ("ours", "rolling_summary")
              else create(cfg, limit=limit))
    sim = Simulator(scenario)
    events = {e.id: e for sess in scenario.sessions for e in sess.events}
    tool_events = {(e.tool, json.dumps(e.args, sort_keys=True)): e for e in events.values() if e.type == "tool_data"}
    by_session: dict[int, list[Entry]] = {}
    for e in entries(scenario):
        by_session.setdefault(e.session, []).append(e)
    task_id = f"task-{scenario.id}"
    trace: list[dict] = []
    calls: list[dict] = []
    checkpoints: list[dict] = []
    written_events: set[str] = set()
    state = {"clock": 0, "memory_s": 0.0, "n_notes": 0}

    def drain(session: int) -> float:
        """Record the model calls a memory system made on its own; return their latency."""
        total = 0.0
        for role, out in system.drain_llm_calls():
            calls.append(_call_record(role, session, out))
            total += out.latency_s
        return total

    def write(entry: Entry, session: int, event_id: str | None = None) -> None:
        state["clock"] += 1
        entry = dataclasses.replace(entry, clock=state["clock"])
        t0 = time.perf_counter()
        system.write(entry)
        state["memory_s"] += time.perf_counter() - t0
        trace.append({"op": "write", "clock": entry.clock, "entry_id": entry.id, "scope": entry.scope,
                      "trust": entry.trust, "author": entry.author, "kind": entry.kind, "session": session})
        if event_id:
            written_events.add(event_id)

    def read(role: str, session: int, query: str):
        reader = Reader(role=role, task_id=task_id, session=session, query=query)
        t0 = time.perf_counter()
        ctx = system.context(reader)
        state["memory_s"] += time.perf_counter() - t0
        trace.append({"op": "read", "clock": state["clock"], "reader": role, "item_ids": [i.id for i in ctx.items],
                      "token_count": ctx.token_count})
        trace.extend(dict(t, clock=state["clock"]) for t in getattr(system, "last_trace", []))
        return ctx

    def agent(role: str, session: int, ctx, task: str, **kw) -> AgentResult:
        res = run_agent(llm, role, context=ctx.render(), task=task, session=session, **kw)
        calls.extend(_call_record(role, session, c) for c in res.calls)
        for c in res.calls:
            trace.append({"op": "llm_call", "clock": state["clock"], "role": role, "session": session,
                          "refusal": c.refusal, "latency_s": round(c.latency_s, 3), "cost_usd": c.usage.cost_usd})
        return res

    def notes(role: str, session: int, res: AgentResult, tool_entry_id: str | None = None) -> None:
        for text in (res.action or {}).get("notes", []):
            state["n_notes"] += 1
            derived = role == "worker" and tool_entry_id is not None
            write(Entry(id=f"n-{session}-{role}-{state['n_notes']}", clock=0, session=session, author=role,
                        kind="agent_note", text=text, scope="task", source="tool" if derived else "agent",
                        trust="untrusted" if derived else "agent", origin=tool_entry_id, task_id=task_id), session)

    for k in range(1, scenario.n_sessions + 1):
        sess_entries = by_session.get(k, [])
        for e in sess_entries:
            ev = events[e.id]
            if e.kind == "user_message" or (e.kind in ("agent_note", "draft") and ev.factor):
                write(e, k, e.id)
        user_text = " ".join(e.text for e in sess_entries if e.kind == "user_message")
        cps = {cp.role: cp for cp in scenario.checkpoints if cp.session == k}

        # Planner
        planner_task = cps["planner"].task_text if "planner" in cps else GENERIC_PLANNER_TASK
        ctx_p = read("planner", k, user_text + " " + planner_task)
        planner = agent("planner", k, ctx_p, planner_task, user_message=user_text)
        notes("planner", k, planner)

        # Worker: choose one action, then report
        worker_task = (cps["worker"].task_text if "worker" in cps
                       else (planner.action or {}).get("answer") or FALLBACK_WORKER_TASK)
        ctx_w = read("worker", k, worker_task)
        src = session_source(scenario, k)
        sources = [_source_line(src)] if src else []
        w1 = agent("worker", k, ctx_w, worker_task, sources=sources)
        a1 = w1.action or {"tool": "none", "args": {}, "answer": "", "notes": []}
        actions, tool_entry_id, tool_result = [], None, "(no tool was used)"
        if a1["tool"] in ("read_document", "read_status"):
            tool_result = sim.call(a1["tool"], a1["args"])
            ev = tool_events.get((a1["tool"], json.dumps(a1["args"], sort_keys=True)))
            if ev is not None:
                tool_entry_id = ev.id
                kind = "document" if a1["tool"] == "read_document" else "tool_output"
                write(Entry(id=ev.id, clock=0, session=k, author="worker", kind=kind, text=tool_result, scope="task",
                            source="document" if kind == "document" else "tool", trust="untrusted", origin=None,
                            task_id=task_id), k, ev.id)
        elif a1["tool"] == "update_record":
            tool_result = sim.call("update_record", a1["args"])
        if a1["tool"] != "none":
            actions.append({"tool": a1["tool"], "args": a1["args"]})
        w2 = agent("worker", k, ctx_w, worker_task, sources=sources, tool_result=tool_result)
        a2 = w2.action or {"tool": "none", "args": {}, "answer": "", "notes": []}
        if a2["tool"] == "update_record":
            sim.call("update_record", a2["args"])
            actions.append({"tool": "update_record", "args": a2["args"]})
        notes("worker", k, w2, tool_entry_id)

        # Reviewer
        review_task = cps["reviewer"].task_text if "reviewer" in cps else f"Review this result: {a2['answer']}"
        ctx_r = read("reviewer", k, review_task)
        reviewer = agent("reviewer", k, ctx_r, review_task)
        notes("reviewer", k, reviewer)

        # Checkpoints of this session
        results = {"planner": (planner, ctx_p), "worker": (w2, ctx_w), "reviewer": (reviewer, ctx_r)}
        for role, cp in cps.items():
            res, ctx = results[role]
            refused = res.refusal or (role == "worker" and w1.refusal)
            action = res.action or {"tool": "none", "args": {}, "answer": "", "notes": []}
            output = {"answer": action["answer"], "actions": actions if role == "worker" else []}
            label = label_failure(scenario, cp.id, refusal=refused, written_event_ids=written_events,
                                  context=ctx, agent_output=None if refused else output)
            passed = (not refused) and score_action(scenario, cp.id, output).passed
            ctx_ok = score_context(scenario, cp.id, ctx).passed
            checkpoints.append({"checkpoint": cp.id, "role": role, "kind": cp.kind, "factor": cp.factor,
                                "session": k, "passed": passed, "label": label, "context_passed": ctx_ok,
                                "answer": action["answer"], "actions": actions if role == "worker" else [],
                                "token_count": ctx.token_count, "refusal": refused,
                                "violations": [] if passed else score_action(scenario, cp.id, output).violations})
            trace.append({"op": "check", "clock": state["clock"], "checkpoint_id": cp.id, "passed": passed})
            trace.append({"op": "label", "clock": state["clock"], "checkpoint_id": cp.id, "label": label})

        t0 = time.perf_counter()
        system.end_session(k)
        elapsed = time.perf_counter() - t0
        state["memory_s"] += max(0.0, elapsed - drain(k))

    totals = {"llm_calls": len(calls), "refusals": sum(c["refusal"] for c in calls),
              "cost_usd": round(sum(c["cost_usd"] for c in calls), 6),
              "llm_latency_s": round(sum(c["latency_s"] for c in calls), 3),
              "memory_s": round(state["memory_s"], 4),
              "input_tokens": sum(c["input_tokens"] + c["cache_creation_tokens"] + c["cache_read_tokens"] for c in calls),
              "output_tokens": sum(c["output_tokens"] for c in calls)}
    extractor = getattr(system, "_extractor", None)
    memory = {"quarantined": len(getattr(system, "quarantined", [])),
              "extraction_refusals": len(getattr(system, "refusals", [])),
              "parse_errors": getattr(extractor, "parse_errors", 0)}
    return {"scenario": scenario.id, "system": cfg, "repeat": repeat, "checkpoints": checkpoints, "calls": calls,
            "memory": memory,
            "totals": totals, "trace": trace, "actions": list(sim.action_log)}
