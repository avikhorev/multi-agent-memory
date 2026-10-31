"""The live session loop with scripted model replies: call counts, labels, memory writes, accounting."""
import json
import re

import pytest

from mam.generate import generate
from mam.live import run_live
from mam.llm import FakeClient


def action(tool="none", args=None, answer="ok", notes=()):
    return json.dumps({"tool": tool, "args": args or {}, "answer": answer, "notes": list(notes)})


def model(answer_for=None, tool_for_worker=None, refuse_role=None, extractor_facts=None):
    """A scripted model that answers by role."""
    def reply(system, messages):
        prompt = messages[0]["content"]
        if system.startswith("You extract"):
            return json.dumps({"facts": extractor_facts or []})
        if system.startswith("You maintain"):
            return "summary text"
        role = "planner" if "Planner" in system else "worker" if "Worker" in system else "reviewer"
        if role == refuse_role:
            return None
        if role == "worker" and "TOOL RESULT" not in prompt:
            if tool_for_worker:
                return action(*tool_for_worker)
            src = re.search(r"(read_document|read_status) (\{[^}]*\})", prompt)
            return action(src.group(1), json.loads(src.group(2))) if src else action()
        return action(answer=(answer_for(role, prompt) if answer_for else "ok"),
                      notes=["worker note"] if role == "worker" else [])
    return reply


def calls_by_role(res):
    out = {}
    for c in res["calls"]:
        out[c["role"]] = out.get(c["role"], 0) + 1
    return out


def test_four_agent_calls_per_session_and_no_extractor_calls_for_full_history():
    s = generate("C0", 0)
    res = run_live(s, "full_history", FakeClient(model()))
    assert calls_by_role(res) == {"planner": 10, "worker": 20, "reviewer": 10}
    assert res["totals"]["llm_calls"] == 40 and res["repeat"] == 0


def test_ours_adds_one_extraction_call_per_source_entry():
    s = generate("C0", 0)
    res = run_live(s, "ours", FakeClient(model()))
    assert calls_by_role(res)["extractor"] >= 10  # at least every user message
    assert {"planner", "worker", "reviewer"} <= set(calls_by_role(res))


def test_a_checkpoint_gets_a_label_and_the_questions_context():
    s = generate("C1", 100, variant="explicit")
    cp = next(c for c in s.checkpoints if c.factor)
    res = run_live(s, "full_history", FakeClient(model(answer_for=lambda role, p: cp.answer.expect)))
    rec = next(r for r in res["checkpoints"] if r["checkpoint"] == cp.id)
    assert rec["role"] == cp.role and rec["answer"] == cp.answer.expect
    assert rec["label"] == "ok" and rec["passed"]


def test_a_wrong_answer_with_a_right_context_is_a_model_error():
    s = generate("C0", 0)
    res = run_live(s, "full_history", FakeClient(model(answer_for=lambda role, p: "no idea")))
    bad = [r for r in res["checkpoints"] if not r["passed"]]
    assert bad and {r["label"] for r in bad} == {"model"}


def test_a_missing_fact_in_memory_is_a_memory_error():
    s = generate("C1", 100, variant="explicit")
    res = run_live(s, "ours", FakeClient(model(answer_for=lambda role, p: "no idea", extractor_facts=[])))
    rec = next(r for r in res["checkpoints"] if r["factor"])
    assert rec["label"] == "memory" and not rec["context_passed"]


def test_a_refusal_that_repeats_is_labelled_refusal_and_counted():
    s = generate("C1", 100, variant="explicit")
    cp = next(c for c in s.checkpoints if c.factor)
    res = run_live(s, "full_history", FakeClient(model(refuse_role=cp.role)))
    rec = next(r for r in res["checkpoints"] if r["checkpoint"] == cp.id)
    assert rec["label"] == "refusal" and res["totals"]["refusals"] >= 2


def test_the_forbidden_update_is_recorded_as_the_workers_action():
    s = generate("C2", 200)
    cp = next(c for c in s.checkpoints if c.factor)
    pat = cp.action.forbidden[0]
    res = run_live(s, "full_history", FakeClient(model(tool_for_worker=("update_record", dict(pat.args, value="x")))))
    rec = next(r for r in res["checkpoints"] if r["checkpoint"] == cp.id)
    assert any(a["tool"] == "update_record" for a in rec["actions"]) and rec["label"] != "ok"


def test_worker_notes_after_reading_a_document_are_stored_as_untrusted():
    s = generate("C5", 500)
    res = run_live(s, "full_history", FakeClient(model()))
    writes = res["trace"] and [t for t in res["trace"] if t["op"] == "write"]
    read_sessions = {t["session"] for t in writes if t["kind"] in ("document", "tool_output")}
    notes = [t for t in writes if t["kind"] == "agent_note" and t["author"] == "worker"]
    assert read_sessions and notes
    for t in notes:
        assert (t["trust"] == "untrusted") == (t["session"] in read_sessions)
    assert any(t["kind"] == "user_message" for t in writes)


def test_memory_time_is_separate_from_model_time():
    res = run_live(generate("C0", 0), "ours", FakeClient(model()))
    t = res["totals"]
    assert t["memory_s"] >= 0 and t["llm_latency_s"] >= 0 and t["cost_usd"] == 0
    for c in res["calls"]:
        assert {"role", "session", "input_tokens", "output_tokens", "cost_usd", "latency_s", "refusal"} <= c.keys()


def test_the_result_is_json_serialisable():
    json.dumps(run_live(generate("C0", 0), "sliding_window", FakeClient(model())))


def test_the_result_reports_what_the_memory_did_on_its_own():
    res = run_live(generate("C0", 0), "ours", FakeClient(model()))
    assert set(res["memory"]) == {"quarantined", "extraction_refusals", "parse_errors"}
    assert run_live(generate("C0", 0), "full_history", FakeClient(model()))["memory"]["parse_errors"] == 0
