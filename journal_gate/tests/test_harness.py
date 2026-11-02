import dataclasses
import json
import re

import pytest

from mam import live
from mam.generate import generate
from mam.live import run_live
from mam.llm import FakeClient

from journal_gate.harness import install

UPDATE = {"tool": "update_record", "args": {"field": "f", "value": "v"}, "answer": "done", "notes": []}


def action(tool="none", args=None, answer="ok"):
    return json.dumps({"tool": tool, "args": args or {}, "answer": answer, "notes": []})


class Model:
    """Scripted model. At the target session the Worker asks for update_record on its first call and on the retry
    after a refusal; with second_too also on its second call."""

    def __init__(self, target, allow=False, second_too=False, retry_update=True):
        self.target, self.allow, self.second_too, self.retry_update = target, allow, second_too, retry_update
        self.gate_calls = self.retries = 0

    def __call__(self, system, messages):
        prompt = messages[0]["content"]
        if system.startswith("You extract"):
            return json.dumps({"facts": []})
        if system.startswith("You check"):
            self.gate_calls += 1
            if self.allow:
                return json.dumps({"allow": True, "quote": "", "reason": "fine"})
            quote = re.search(r"\[session \d+\] (.*)", prompt).group(1)
            return json.dumps({"allow": False, "quote": quote, "reason": "frozen"})
        role = "planner" if "Planner" in system else "worker" if "Worker" in system else "reviewer"
        if role == "worker":
            session = int(re.search(r"SESSION (\d+)", prompt).group(1))
            refused = "REFUSED by the project gate" in prompt
            self.retries += refused and session == self.target
            if session == self.target and ("TOOL RESULT" not in prompt or self.second_too
                                           or (refused and self.retry_update)):
                return action("update_record", {"field": "f", "value": "v"})
            if "TOOL RESULT" not in prompt:
                src = re.search(r"tool: (read_document|read_status), args: (\{[^}]*\})", prompt)
                return action(src.group(1), json.loads(src.group(2))) if src else action()
        return action()


class Priced:
    """Every call costs one cent."""

    def __init__(self, inner):
        self.inner = inner

    @property
    def calls(self):
        return self.inner.calls

    def complete(self, system, messages, options):
        out = self.inner.complete(system, messages, options)
        return dataclasses.replace(out, usage=dataclasses.replace(out.usage, cost_usd=0.01))


@pytest.fixture
def play(monkeypatch, tmp_path):
    monkeypatch.setattr(live, "create", live.create)  # restored after the test
    monkeypatch.setattr(live, "run_agent", live.run_agent)

    def go(cfg, target, **kw):
        model, log = Model(target, **kw), tmp_path / "gate_log.jsonl"
        llm = Priced(FakeClient(model))
        install(llm, log)
        res = run_live(generate("C2", 200), cfg, llm)
        rows = [json.loads(l) for l in log.read_text().splitlines()] if log.exists() else []
        return res, model, llm, rows
    return go


def test_a_refused_update_does_not_reach_the_record_and_the_extra_action_is_one_per_session(play):
    res, model, _, rows = play("journal_gate", 1, second_too=True)
    assert res["actions"] == []
    assert model.retries == 1  # the Worker asked three times in the session but was given one extra action
    assert [(r["call"], r["attempt"], r["stage"]) for r in rows] == [
        ("first", 0, "user_rule"), ("first", 1, "user_rule"), ("second", 0, "user_rule")]
    assert rows[0]["system"] == "journal_gate" and rows[0]["task_id"] == "task-C2-dev-0200"
    assert (rows[0]["field"], rows[0]["value"], rows[0]["allow"]) == ("f", "v", False) and rows[0]["quote"]


def test_an_allowed_update_is_executed(play):
    res, model, _, rows = play("journal_gate", 1, allow=True)
    assert res["actions"] == [{"tool": "update_record", "args": {"field": "f", "value": "v"}}]
    assert model.retries == 0 and [(r["stage"], r["allow"]) for r in rows] == [("passed", True)]


def test_gate_calls_are_counted_in_the_cost(play):
    res, model, llm, _ = play("journal_gate", 1, second_too=True)
    assert model.gate_calls == 3
    assert res["totals"]["llm_calls"] == len(llm.calls)  # extractor, agent and gate calls alike
    assert res["totals"]["cost_usd"] == pytest.approx(0.01 * len(llm.calls))


def test_an_unread_source_is_refused_without_a_gate_call(play):
    res, model, _, rows = play("journal_gate", 2, retry_update=False)  # session 2 offers a source
    assert res["actions"] == []
    assert model.gate_calls == 0 and [r["stage"] for r in rows] == ["unread_source"]


@pytest.mark.parametrize("cfg", ["journal", "ours3", "full_history"])
def test_other_systems_are_not_guarded(play, cfg):
    res, model, _, rows = play(cfg, 1)
    assert [a["tool"] for a in res["actions"]] == ["update_record"]
    assert model.gate_calls == 0 and rows == []
