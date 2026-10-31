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
