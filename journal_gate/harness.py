"""Wiring of the journal and the gate into mam.live without changing src/mam.

install() replaces mam.live.create and mam.live.run_agent. Units run in threads, so the state of the unit that is
running (memory system, gate, sessions that used their extra action) is kept per thread.
"""
import json
import threading
from types import SimpleNamespace

from mam import agents, live
from mam.agents import AgentResult
from mam.systems import create as base_create
from post_hoc_ours2 import Ours3

from journal_gate.gate import Gate
from journal_gate.memory import Journal

NO_TOOL = "(no tool was used)"
_local = threading.local()
_log_lock = threading.Lock()


def install(llm, log_path):
    def create(name, **kw):
        limit = kw.get("limit", 2000)
        gate = Gate(llm) if name == "journal_gate" else None
        if name in ("journal", "journal_gate"):
            system = Journal(limit, extractor="llm", llm=llm)
        elif name == "ours3":
            system = Ours3(limit, extractor="llm", llm=llm)
        else:
            system = base_create(name, **kw)
        _local.run = SimpleNamespace(name=name, system=system, gate=gate, used=set())
        return system

    def log(run, session, call, attempt, action, d):
        args = action["args"]
        task_id = next((e.task_id for e in run.system._entries.values()), "")
        row = {"system": run.name, "task_id": task_id, "session": session, "call": call, "attempt": attempt,
               "field": args.get("field"), "value": args.get("value"), "allow": d.allow, "stage": d.stage,
               "reason": d.reason, "quote": d.quote}
        with _log_lock, open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")

    def is_update(action):
        return bool(action) and action["tool"] == "update_record"

    def guarded(llm_, role, **kw):
        res = agents.run_agent(llm_, role, **kw)
        run = getattr(_local, "run", None)
        if run is None or run.gate is None or role != "worker" or not is_update(res.action):
            return res
        tr, session = kw.get("tool_result"), kw.get("session")
        offered = bool(kw.get("sources"))
        read = tr is not None and tr != NO_TOOL and not tr.startswith("ERROR")
        calls = list(res.calls)

        def ask(action, attempt):
            before = len(run.gate.calls)
            d = run.gate.check(action["args"], run.system.user_messages(), offered, read)
            calls.extend(run.gate.calls[before:])
            log(run, session, "first" if tr is None else "second", attempt, action, d)
            return d

        refused = res.action
        d = ask(refused, 0)
        if d.allow:
            res.calls = calls
            return res
        if session not in run.used:
            run.used.add(session)
            msg = (f"REFUSED by the project gate: {d.reason}. The change was not made. "
                   "Choose your next action.")
            res2 = agents.run_agent(llm_, role, **dict(kw, tool_result=msg))
            calls.extend(res2.calls)
            res = AgentResult(res2.action, res2.refusal, res2.error, calls)
            if not is_update(res2.action):
                return res
            refused = res2.action
            if ask(refused, 1).allow:
                return res
        res.calls = calls
        res.action = {"tool": "none", "args": {}, "answer": refused["answer"], "notes": refused["notes"]}
        return res

    live.create = create
    live.run_agent = guarded
