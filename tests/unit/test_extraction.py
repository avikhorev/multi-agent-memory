"""The extraction pass: model answers saved once, replayed later without a model."""
import json

import pytest

from mam.extract import CacheExtractor
from mam.extraction import Pass, merge_rows, run_pass
from mam.generate import generate
from mam.llm import FakeClient, LLMResult, Usage
from mam.simulate import entries
from mam.systems import create
from mam.types import Entry, Reader

ROW = {"entity": "Atlas/billing", "attribute": "budget_usd", "value": "100", "as_of": None}


def reply(system, messages):
    if system.startswith("You extract"):
        return json.dumps({"facts": [ROW]})
    if system.startswith("You maintain"):
        return "billing budget 100"
    raise AssertionError("unexpected role")


class Costly:
    def __init__(self, cost):
        self.cost, self.n = cost, 0

    def complete(self, system, messages, options):
        self.n += 1
        return LLMResult(reply(system, messages), Usage(cost_usd=self.cost), 0.0)


def scenario_dir(tmp_path, *ids):
    d = tmp_path / "data"
    d.mkdir()
    from mam.scenario import dump
    for sid in ids:
        cat, _, seed = sid.partition("-dev-")
        dump(generate(cat, int(seed) + int(cat[1]) * 100), d / f"{sid}.json")
    return d


def load_rows(path):
    return [json.loads(l) for l in open(path)]


def test_one_scenario_gives_an_entry_row_per_source_and_a_summary_row_per_session(tmp_path):
    data = scenario_dir(tmp_path, "C0-dev-0000")
    report = run_pass(["C0-dev-0000"], FakeClient(reply), data, tmp_path / "out", workers=1)
    rows = load_rows(tmp_path / "out" / "scenarios" / "C0-dev-0000.jsonl")
    s = generate("C0", 0)
    sources = [e for e in entries(s) if e.kind in ("user_message", "tool_output", "document")]
    assert report.done == 1 and report.refusals == 0
    assert [r["entry_id"] for r in rows if r["kind"] == "entry"] == [e.id for e in sources]
    sums = [r for r in rows if r["kind"] == "summary"]
    assert [r["session"] for r in sums] == list(range(1, 11)) and sums[0]["text"] == "billing budget 100"
    assert all(r["task_id"] == "task-C0-dev-0000" and r["scenario"] == "C0-dev-0000" for r in rows)
    first = next(r for r in rows if r["kind"] == "entry")
    assert first["facts"] == [{"entity": "Atlas/billing", "attribute": "budget_usd", "value": "100",
                               "event_time": -1, "source": first["facts"][0]["source"]}] and not first["refusal"]


def test_a_refused_extraction_and_a_refused_summary_are_saved_and_counted(tmp_path):
    data = scenario_dir(tmp_path, "C0-dev-0000")
    report = run_pass(["C0-dev-0000"], FakeClient(lambda s, m: None), data, tmp_path / "out", workers=1)
    rows = load_rows(tmp_path / "out" / "scenarios" / "C0-dev-0000.jsonl")
    assert all(r["refusal"] for r in rows) and all(r["facts"] == [] for r in rows if r["kind"] == "entry")
    assert all(r["text"] == "" for r in rows if r["kind"] == "summary")
    assert report.refusals == len(rows) and report.entry_refusals + report.summary_refusals == report.refusals


def test_finished_scenarios_are_skipped_and_the_cost_limit_stops_new_ones(tmp_path):
    data = scenario_dir(tmp_path, "C0-dev-0000", "C0-dev-0001", "C0-dev-0002")
    ids = ["C0-dev-0000", "C0-dev-0001", "C0-dev-0002"]
    llm = Costly(0.01)
    first = run_pass(ids, llm, data, tmp_path / "out", workers=1, max_cost_usd=0.5)
    assert 1 <= first.done < 3 and first.stopped_by == "cost"
    calls_after_first = llm.n
    second = run_pass(ids[: first.done], llm, data, tmp_path / "out", workers=1)
    assert second.skipped == first.done and second.done == 0 and llm.n == calls_after_first


def test_the_time_limit_stops_new_scenarios(tmp_path):
    data = scenario_dir(tmp_path, "C0-dev-0000", "C0-dev-0001")
    ticks = iter(range(0, 10_000, 100))
    report = run_pass(["C0-dev-0000", "C0-dev-0001"], FakeClient(reply), data, tmp_path / "out", workers=1,
                      max_minutes=1, now=lambda: next(ticks))
    assert report.stopped_by == "time" and report.done < 2


def test_the_merged_cache_is_ordered_and_replays_into_the_same_facts(tmp_path):
    data = scenario_dir(tmp_path, "C0-dev-0000", "C1-dev-0000")
    run_pass(["C1-dev-0000", "C0-dev-0000"], FakeClient(reply), data, tmp_path / "out", workers=1)
    merged = tmp_path / "cache.jsonl"
    n = merge_rows(tmp_path / "out", merged)
    rows = load_rows(merged)
    assert n == len(rows) and [r["scenario"] for r in rows] == sorted(r["scenario"] for r in rows)
    cache = CacheExtractor(merged)
    e = next(x for x in entries(generate("C1", 100, variant="explicit")) if x.kind == "user_message")
    (fact,) = cache.extract(e).facts
    assert (fact.entity, fact.attribute, fact.value) == ("Atlas/billing", "budget_usd", "100")


def test_the_same_entry_id_in_two_scenarios_does_not_collide(tmp_path):
    rows = [{"kind": "entry", "scenario": "a", "task_id": "task-a", "entry_id": "e-0001", "session": 1, "refusal": False,
             "constraints": [], "facts": [{"entity": "Atlas", "attribute": "owner", "value": "A", "event_time": -1, "source": "user"}]},
            {"kind": "entry", "scenario": "b", "task_id": "task-b", "entry_id": "e-0001", "session": 1, "refusal": False,
             "constraints": [], "facts": [{"entity": "Atlas", "attribute": "owner", "value": "B", "event_time": -1, "source": "user"}]}]
    path = tmp_path / "c.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows))
    cache = CacheExtractor(path)

    def e(task):
        return Entry(id="e-0001", clock=1, session=1, author="user", kind="user_message", text="t", scope="task",
                     source="user", trust="trusted", origin=None, task_id=task)
    assert cache.extract(e("task-a")).facts[0].value == "A" and cache.extract(e("task-b")).facts[0].value == "B"


def summary_rows(tmp_path, texts, refused=()):
    rows = [{"kind": "summary", "scenario": "s", "task_id": "t", "session": i + 1, "text": "" if (i + 1) in refused else t,
             "refusal": (i + 1) in refused} for i, t in enumerate(texts)]
    path = tmp_path / "c.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows))
    return path


def feed(system, upto):
    for k in range(1, upto + 1):
        system.write(Entry(id=f"e{k}", clock=k, session=k, author="user", kind="user_message", text="x", scope="task",
                           source="user", trust="trusted", origin=None, task_id="t"))
        system.end_session(k)


def test_the_cached_summary_is_the_latest_one_up_to_the_ended_session(tmp_path):
    s = create("rolling_summary", extractor="cache", cache_path=summary_rows(tmp_path, ["one", "two", "three"]))
    feed(s, 2)
    assert [i.text for i in s.context(Reader("planner", "t", 3, "q")).items] == ["two"]


def test_a_refused_summary_keeps_the_previous_one_and_is_counted(tmp_path):
    s = create("rolling_summary", extractor="cache", cache_path=summary_rows(tmp_path, ["one", "two"], refused={2}))
    feed(s, 2)
    assert [i.text for i in s.context(Reader("planner", "t", 3, "q")).items] == ["one"] and s.refusals == [2]


def test_the_cached_summary_is_trimmed_to_the_limit_and_empty_without_rows(tmp_path):
    from mam.tokens import count
    long = "\n".join(f"line {i} with some words" for i in range(60))
    s = create("rolling_summary", extractor="cache", cache_path=summary_rows(tmp_path, [long]), limit=40)
    feed(s, 1)
    ctx = s.context(Reader("planner", "t", 2, "q"))
    assert 0 < ctx.token_count <= 40 and count(ctx.items[0].text) == ctx.token_count
    empty = create("rolling_summary", extractor="cache", cache_path=summary_rows(tmp_path, []))
    feed(empty, 1)
    assert empty.context(Reader("planner", "t", 2, "q")).items == []
