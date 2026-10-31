"""Tables of live results from saved unit files, checked on small synthetic units."""
import json

from mam.live_tables import load_units, paired_counts, render, slope, summarize


def cp(cid, label, factor=True, role="planner", violations=(), reachable=True):
    return {"checkpoint": cid, "role": role, "kind": "value", "factor": factor, "session": 7, "passed": label == "ok",
            "label": label, "context_passed": label != "memory", "reachable": reachable, "violations": list(violations),
            "refusal": label == "refusal"}


def call(session, role="planner", inp=100, out=10, cost=0.001, lat=2.0, refusal=False):
    return {"role": role, "session": session, "input_tokens": inp, "cache_creation_tokens": 0, "cache_read_tokens": 0,
            "output_tokens": out, "cost_usd": cost, "latency_s": lat, "refusal": refusal}


def unit(system, scenario, repeat, cps, n_sessions=10, calls=None, memory_s=0.5):
    calls = calls or [call(s) for s in range(1, n_sessions + 1)]
    return {"manifest": {"system": system, "scenario": scenario, "repeat": repeat}, "checkpoints": cps, "calls": calls,
            "totals": {"cost_usd": sum(c["cost_usd"] for c in calls), "llm_latency_s": sum(c["latency_s"] for c in calls),
                       "memory_s": memory_s, "llm_calls": len(calls), "refusals": sum(c["refusal"] for c in calls)},
            "cost_usd": sum(c["cost_usd"] for c in calls)}


UNITS = [
    unit("ours", "C1-eval-1", 0, [cp("a", "ok")]), unit("ours", "C1-eval-1", 1, [cp("a", "ok")]),
    unit("ours", "C1-eval-2", 0, [cp("a", "memory")]), unit("ours", "C1-eval-2", 1, [cp("a", "agent")]),
    unit("full_history", "C1-eval-1", 0, [cp("a", "memory")]), unit("full_history", "C1-eval-1", 1, [cp("a", "ok")]),
    unit("full_history", "C1-eval-2", 0, [cp("a", "refusal")]), unit("full_history", "C1-eval-2", 1, [cp("a", "ok")]),
]


def test_successes_labels_and_repeat_range_per_system_and_category():
    s = summarize(UNITS)["C1"]
    ours, full = s["ours"], s["full_history"]
    assert (ours["ok"], ours["n"]) == (2, 4) and ours["labels"] == {"ok": 2, "memory": 1, "agent": 1}
    assert (full["ok"], full["n"]) == (2, 4) and full["labels"]["refusal"] == 1
    assert ours["repeat_range"] == (0.5, 0.5) and full["repeat_range"] == (0.0, 1.0)


def test_the_conditional_rate_leaves_out_checkpoints_whose_information_never_reached_memory():
    ours = summarize(UNITS)["C1"]["ours"]
    assert (ours["ok_given_in_memory"], ours["n_in_memory"]) == (2, 3)
    unreachable = summarize([unit("ours", "C1-eval-1", 0, [cp("a", "agent", reachable=False)])])["C1"]["ours"]
    assert unreachable["n_reachable"] == 0


def test_only_the_controlled_checkpoint_counts_except_in_c0_and_c6():
    base = cp("b", "memory", factor=False)
    s = summarize([unit("ours", "C1-eval-1", 0, [cp("a", "ok"), base]), unit("ours", "C0-eval-1", 0, [cp("a", "ok", factor=False), base])])
    assert s["C1"]["ours"]["n"] == 1 and s["C0"]["ours"]["n"] == 2


def test_paired_counts_compare_two_systems_on_the_same_scenario_repeat_and_checkpoint():
    assert paired_counts(UNITS, "ours", "full_history") == {"C1": {"a_only": 1, "b_only": 1, "both": 1, "neither": 1}}


def test_refusals_are_shown_as_a_share_per_system_and_category():
    text = render(UNITS)
    assert "refusal" in text and "25%" in text  # 1 of 4 checkpoints of full_history in C1


def test_cost_tokens_and_time_per_step_are_reported_per_system():
    s = summarize([unit("ours", "C0-eval-1", 0, [cp("a", "ok", factor=False)], calls=[call(k, inp=200, out=20, cost=0.002, lat=3.0) for k in range(1, 11)])])
    cost = s["_cost"]["ours"]
    assert cost["input_tokens_per_call"] == 200 and cost["cost_per_call"] == 0.002 and cost["llm_s_per_call"] == 3.0
    assert cost["memory_s_per_session"] == 0.05


def test_the_slope_is_tokens_per_extra_session_across_lengths():
    assert slope([(10, 100.0), (20, 200.0), (30, 300.0)]) == 10.0
    assert slope([(10, 100.0)]) is None


def test_the_c6_curve_uses_the_lengths_of_the_units():
    units = [unit("full_history", f"C6-eval-{n}", 0, [cp("a", "ok", factor=False)], n_sessions=n,
                  calls=[call(k, inp=50 * n) for k in range(1, n + 1)]) for n in (10, 20, 30)]
    assert summarize(units)["_c6"]["full_history"]["slope_input_tokens"] == 50.0


def test_attack_success_is_reported_overall_and_among_exposed_units(tmp_path):
    attacked = cp("a", "model", violations=["forbidden action performed: update_record {'field': 'approval_mode'}"])
    units = [unit("full_history", "C5-eval-1", 0, [attacked]), unit("full_history", "C5-eval-2", 0, [cp("a", "ok")])]
    traces = tmp_path / "traces"
    traces.mkdir()
    (traces / "full_history__C5-eval-1__r0.jsonl").write_text(json.dumps({"op": "write", "kind": "document", "entry_id": "x-0001"}) + "\n")
    (traces / "full_history__C5-eval-2__r0.jsonl").write_text(json.dumps({"op": "write", "kind": "user_message", "entry_id": "e-0001"}) + "\n")
    c5 = summarize(units, traces_dir=traces)["_c5"]["full_history"]
    assert (c5["units"], c5["exposed"], c5["attacked"], c5["attacked_exposed"]) == (2, 1, 1, 1)


def test_units_are_loaded_from_the_directory(tmp_path):
    (tmp_path / "units").mkdir()
    (tmp_path / "units" / "x.json").write_text(json.dumps(UNITS[0]))
    assert load_units(tmp_path) == [UNITS[0]]
