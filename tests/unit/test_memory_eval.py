"""The memory-level runner and the interval code, through their public functions."""
import json

from mam.generate import generate
from mam.memory_eval import make_system, run_scenario
from mam.tables import interval, render


def test_a_scenario_run_is_deterministic_and_covers_every_checkpoint():
    s = generate("C1", 100, variant="explicit")
    a, _ = run_scenario("ours@oracle", s)
    b, _ = run_scenario("ours@oracle", s)
    assert a == b
    cps = [r for r in a if r["record"] == "checkpoint"]
    assert [r["checkpoint"] for r in cps] == [c.id for c in sorted(s.checkpoints, key=lambda c: c.session)]
    assert a[-1]["record"] == "scenario" and a[-1]["system"] == "ours@oracle"


def test_the_oracle_variant_passes_and_full_history_shows_the_stale_value():
    s = generate("C1", 100, variant="explicit")
    ours, _ = run_scenario("ours@oracle", s)
    full, _ = run_scenario("full_history", s)
    factor = lambda recs: next(r for r in recs if r["record"] == "checkpoint" and r["factor"])
    assert factor(ours)["passed"] and not factor(ours)["stale_present"]
    assert not factor(full)["passed"] and factor(full)["stale_present"]


def test_constraints_that_do_not_fit_are_recorded_as_a_failure_not_a_crash():
    s = generate("C2", 200)
    recs, _ = run_scenario("ours@oracle", s, limit=3)
    factor = next(r for r in recs if r["record"] == "checkpoint" and r["factor"])
    assert not factor["passed"] and factor["violations"][0].startswith("context error")


def test_ablation_names_map_to_switches():
    assert make_system("ours@oracle-no_trust").ablate == {"trust"}
    assert make_system("rolling_summary@rules").limit == 2000


def test_bootstrap_interval_is_exact_for_constant_data_and_repeatable():
    assert interval([1.0] * 5) == (1.0, 1.0, 1.0)
    data = [0.0, 1.0, 1.0, 0.0, 1.0, 1.0, 1.0]
    assert interval(data) == interval(data)
    mean, lo, hi = interval(data)
    assert lo <= mean <= hi


def test_tables_render_one_row_per_system():
    s = generate("C0", 0)
    rows = []
    for cfg in ("full_history", "ours@oracle"):
        rows += run_scenario(cfg, s)[0]
    text = render({"full_history": rows[: len(rows) // 2], "ours@oracle": rows[len(rows) // 2:]}, "t")
    assert "### C0: correct" in text and text.count("| full_history |") >= 1


def test_the_system_set_gains_the_cache_variants_only_when_a_cache_is_given():
    from mam.memory_eval import systems_for
    plain, cached = systems_for(False), systems_for(True)
    assert "ours@cache" not in plain and "rolling_summary@cache" not in plain
    assert set(plain) < set(cached)
    assert {"ours@cache", "rolling_summary@cache", "ours@cache-no_validity", "ours@cache-no_scopes",
            "ours@cache-no_trust", "ours@cache-no_pinned_constraints"} <= set(cached)


def test_a_cache_variant_reads_the_saved_answers(tmp_path):
    import json
    s = generate("C1", 100, variant="explicit")
    first = next(e for e in entries_of(s) if e.kind == "user_message")
    fact = next(iter(first.oracle_facts))
    cache = tmp_path / "cache.jsonl"
    cache.write_text(json.dumps({"kind": "entry", "task_id": first.task_id, "entry_id": first.id, "refusal": False,
                                 "constraints": [], "facts": [{"entity": fact.entity, "attribute": fact.attribute,
                                                              "value": fact.value, "event_time": fact.valid_from,
                                                              "source": fact.source}]}) + "\n")
    recs, _ = run_scenario("ours@cache", s, cache_path=cache)
    assert [r for r in recs if r["record"] == "scenario"][0]["system"] == "ours@cache"
    with __import__("pytest").raises(ValueError):
        run_scenario("ours@cache", s)  # no cache path: a clear error, not a silent empty memory


def entries_of(s):
    from mam.simulate import entries
    return entries(s)
