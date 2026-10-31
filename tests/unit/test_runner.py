"""The runner: units of work, resume, limits, accounting and what ends up in the files."""
import json
import threading

import pytest

from mam.llm import FakeClient, LLMError, LLMResult, RateLimitTimeout, Usage
from mam.run import (EXIT_OK, EXIT_RATE_LIMITED, Unit, plan_units, run_units, trace_lines)
from mam.selection import select_live

DEV = "data/dev/manifest.json"


def reply_by_role(system, messages):
    if system.startswith("You extract"):
        return json.dumps({"facts": []})
    if system.startswith("You maintain"):
        return "summary"
    return json.dumps({"tool": "none", "args": {}, "answer": "ok", "notes": []})


class CostlyClient:
    """Every call costs a fixed amount; counts calls."""

    def __init__(self, cost=0.1):
        self.cost, self.n, self.lock = cost, 0, threading.Lock()

    def complete(self, system, messages, options):
        with self.lock:
            self.n += 1
        return LLMResult(reply_by_role(system, messages), Usage(cost_usd=self.cost), 0.0)


def units_for(systems=("full_history",), scenarios=("C0-dev-0000",), repeats=1):
    return plan_units(list(systems), list(scenarios), repeats)


def run(tmp_path, units, llm=None, **kw):
    kw.setdefault("workers", 1)
    return run_units(units, llm or FakeClient(reply_by_role), "data/dev", tmp_path, **kw)


def test_units_are_ordered_by_repeat_scenario_and_system():
    units = plan_units(["b", "a"], ["s2", "s1"], 2)
    assert [(u.repeat, u.scenario, u.system) for u in units] == [
        (0, "s2", "b"), (0, "s2", "a"), (0, "s1", "b"), (0, "s1", "a"),
        (1, "s2", "b"), (1, "s2", "a"), (1, "s1", "b"), (1, "s1", "a")]


def test_a_unit_writes_one_result_file_with_a_manifest_and_a_trace(tmp_path):
    report = run(tmp_path, units_for())
    assert report.exit_code == EXIT_OK and report.done == 1
    f = tmp_path / "units" / "full_history__C0-dev-0000__r0.json"
    data = json.loads(f.read_text())
    assert data["manifest"]["system"] == "full_history" and data["manifest"]["model"] == "claude-haiku-5-5"
    assert {"cli_version", "commit", "api_key_set", "started", "finished"} <= data["manifest"].keys()
    assert data["cost_usd"] == data["totals"]["cost_usd"] and data["checkpoints"]
    assert (tmp_path / "traces" / "full_history__C0-dev-0000__r0.jsonl").exists()
    assert not list(tmp_path.rglob("*.tmp"))


def test_finished_units_are_skipped_on_a_second_run(tmp_path):
    run(tmp_path, units_for())
    llm = CostlyClient()
    report = run(tmp_path, units_for(), llm=llm)
    assert report.skipped == 1 and report.done == 0 and llm.n == 0


def test_the_cost_limit_stops_new_units_and_keeps_finished_ones(tmp_path):
    units = units_for(scenarios=("C0-dev-0000", "C0-dev-0001", "C0-dev-0002"))
    report = run(tmp_path, units, llm=CostlyClient(cost=0.1), max_cost_usd=3.0)
    assert 1 <= report.done < 3 and report.stopped_by == "cost"
    assert len(list((tmp_path / "units").glob("*.json"))) == report.done


def test_the_time_limit_stops_new_units(tmp_path):
    ticks = iter(range(0, 10_000, 100))
    report = run(tmp_path, units_for(scenarios=("C0-dev-0000", "C0-dev-0001")), max_minutes=1, now=lambda: next(ticks))
    assert report.stopped_by == "time" and report.done < 2


def test_a_failing_unit_is_reported_and_retried_on_the_next_run(tmp_path):
    class Flaky:
        def complete(self, system, messages, options):
            raise LLMError("boom")
    report = run(tmp_path, units_for(), llm=Flaky())
    assert report.failed == 1 and report.done == 0 and not list((tmp_path / "units").glob("*.json"))
    assert run(tmp_path, units_for()).done == 1


def test_a_rate_limit_that_does_not_clear_ends_the_run_with_its_own_exit_code(tmp_path):
    class Limited:
        def complete(self, system, messages, options):
            raise RateLimitTimeout("limited")
    report = run(tmp_path, units_for(scenarios=("C0-dev-0000", "C0-dev-0001")), llm=Limited())
    assert report.exit_code == EXIT_RATE_LIMITED and report.stopped_by == "rate_limit" and report.done == 0


def test_no_credential_value_reaches_any_file(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-SECRET-VALUE-123")
    run(tmp_path, units_for())
    text = "".join(p.read_text() for p in tmp_path.rglob("*") if p.is_file())
    assert "sk-SECRET-VALUE-123" not in text and '"api_key_set": true' in text


def test_workers_run_in_parallel_without_losing_units(tmp_path):
    units = units_for(systems=("full_history", "sliding_window"), scenarios=("C0-dev-0000", "C0-dev-0001"))
    report = run(tmp_path, units, workers=4)
    assert report.done == 4 and len(list((tmp_path / "units").glob("*.json"))) == 4


def test_the_trace_command_prints_every_line_of_a_scenario(tmp_path):
    run(tmp_path, units_for(systems=("full_history", "sliding_window")))
    lines = list(trace_lines(tmp_path, "C0-dev-0000"))
    assert lines and all(json.loads(l)["op"] for l in lines)
    assert list(trace_lines(tmp_path, "nope")) == []


@pytest.mark.parametrize("size,expected", [("smoke", 7), ("B", 2 * 6 + 3), ("A", 3 * 6 + 3)])
def test_live_selection_sizes(size, expected):
    ids = select_live(DEV, size)
    assert len(ids) == expected and len(set(ids)) == expected and ids == select_live(DEV, size)


def test_selection_keeps_both_update_kinds_in_c1_and_c3():
    manifest = {s["id"]: s for s in json.load(open(DEV))["scenarios"]}
    for size, (implicit, explicit) in {"A": (2, 1), "B": (1, 1)}.items():
        picked = [manifest[i] for i in select_live(DEV, size)]
        for cat in ("C1", "C3"):
            variants = [s["variant"] for s in picked if s["category"] == cat]
            assert (variants.count("implicit"), variants.count("explicit")) == (implicit, explicit)
        c6 = sorted(s["n_sessions"] for s in picked if s["category"] == "C6")
        assert c6 == [10, 20, 30]
