"""Memory-level evaluation: we run the scenarios through the memory system and evaluate the contexts assembled at the checkpoints.

The model is not called, so the results are deterministic and cheap. The timings
(they are nondeterministic) are written separately, to <out>/timing/, so as not to disturb the comparison of results.

  python -m mam.memory_eval --split dev --out results/memory_level/dev [--systems a,b,c]
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from mam.scenario import load
from mam.scoring import score_context
from mam.simulate import entries
from mam.systems import create
from mam.types import Reader

# Ablation name in the configuration -> which mechanism is disabled in the `ours` system.
ABLATIONS = {"no_validity": "validity", "no_scopes": "scopes", "no_trust": "trust",
             "no_pinned_constraints": "pinned_constraints"}
# Configurations "system@extractor[-ablation]": the baselines for comparison, ours with the oracle and the rules, and ours without each mechanism.
DEFAULT_SYSTEMS = (
    ["full_history", "sliding_window", "shared_rag_bm25", "rolling_summary@rules", "ours@oracle", "ours@rules"]
    + [f"ours@oracle-{a}" for a in ABLATIONS])


def systems_for(with_cache: bool) -> list[str]:
    """Variants with the cache (saved model answers) are added only when a cache file is given."""
    if not with_cache:
        return list(DEFAULT_SYSTEMS)
    return DEFAULT_SYSTEMS + ["rolling_summary@cache", "ours@cache"] + [f"ours@cache-{a}" for a in ABLATIONS]


def make_system(cfg: str, limit: int = 2000, cache_path=None):
    """Creates a system from the string cfg: name, name@extractor or name@extractor-ablation."""
    # We parse the string into parts: the name, after "@" the extractor, after "-" the ablation.
    name, _, rest = cfg.partition("@")
    extractor, _, ablation = rest.partition("-")
    kwargs = {"limit": limit}
    if extractor:
        kwargs.update(extractor=extractor, cache_path=cache_path if extractor == "cache" else None)
    if ablation:
        kwargs["ablate"] = {ABLATIONS[ablation]}
    return create(name, **kwargs)


def run_scenario(cfg: str, scenario, limit: int = 2000, cache_path=None):
    """One scenario through one system. Returns (result records, timing measurements)."""
    system = make_system(cfg, limit, cache_path)
    # Entry lines by session numbers: at the end of each session the memory receives its entries.
    by_session: dict[int, list] = {}
    for e in entries(scenario):
        by_session.setdefault(e.session, []).append(e)
    records, t_write, t_read = [], 0.0, 0.0
    for k in range(1, scenario.n_sessions + 1):
        # The checkpoints of session k are checked BEFORE its events are written: the question is asked at the start of the session,
        # when the memory knows only the previous sessions.
        for cp in (c for c in scenario.checkpoints if c.session == k):
            reader = Reader(role=cp.role, task_id=f"task-{scenario.id}", session=k, query=cp.task_text)
            t0 = time.perf_counter()
            try:
                ctx = system.context(reader)
                res = score_context(scenario, cp.id, ctx)
                rec = {"passed": res.passed, "violations": res.violations, "stale_present": res.stale_present,
                       "foreign_private_present": res.foreign_private_present,
                       "attack_in_instruction_slot": res.attack_in_instruction_slot, "token_count": ctx.token_count}
            except ValueError as err:  # e.g. pinned constraints do not fit the limit: this is a failure of the checkpoint, not a crash of the run
                rec = {"passed": False, "violations": [f"context error: {err}"], "stale_present": False,
                       "foreign_private_present": False, "attack_in_instruction_slot": False, "token_count": 0}
            t_read += time.perf_counter() - t0
            # How many required lines the context does not contain (needed for the metric "the current value is present").
            rec["missing_present"] = sum(v.startswith("present missing") for v in rec["violations"])
            rec.update(record="checkpoint", system=cfg, scenario=scenario.id, category=scenario.category,
                       variant=scenario.variant, resolution=scenario.resolution, n_sessions=scenario.n_sessions,
                       checkpoint=cp.id, role=cp.role, kind=cp.kind, factor=cp.factor)
            records.append(rec)
        t0 = time.perf_counter()
        for e in by_session.get(k, []):
            system.write(e)
        system.end_session(k)
        t_write += time.perf_counter() - t0
    # Summary record of the scenario: how many fragments the quarantine held back and how many model refusals there were.
    summary = {"record": "scenario", "system": cfg, "scenario": scenario.id, "category": scenario.category,
               "quarantined": len(getattr(system, "quarantined", [])), "refusals": len(getattr(system, "refusals", []))}
    return records + [summary], {"system": cfg, "scenario": scenario.id, "write_ms": round(t_write * 1000, 2),
                                 "read_ms": round(t_read * 1000, 2)}


def scenario_paths(data_dir: Path) -> list[Path]:
    """Paths to the scenarios in manifest order."""
    manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
    return [data_dir / f"{s['id']}.json" for s in manifest["scenarios"]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True, choices=["dev", "eval", "holdout"])
    ap.add_argument("--data", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--systems", default=None, help="comma-separated; default depends on --cache")
    ap.add_argument("--limit", type=int, default=2000)
    ap.add_argument("--cache", default=None)
    a = ap.parse_args()
    # Data directory: holdout lies separately, the other splits are in data/<split>.
    data_dir = Path(a.data or ("holdout" if a.split == "holdout" else f"data/{a.split}"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    scenarios = [load(p) for p in scenario_paths(data_dir)]
    for cfg in (a.systems.split(",") if a.systems else systems_for(a.cache is not None)):
        rows, timing = [], []
        for s in scenarios:
            recs, tm = run_scenario(cfg, s, a.limit, a.cache)
            rows += recs
            timing.append(tm)
        (out / f"{cfg}.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
        (out / "timing").mkdir(exist_ok=True)
        (out / "timing" / f"{cfg}.jsonl").write_text("".join(json.dumps(t, sort_keys=True) + "\n" for t in timing), encoding="utf-8")
        # For the console: how many checkpoints passed (without the summary records of the scenarios).
        passed = sum(r["passed"] for r in rows if r["record"] == "checkpoint")
        total = sum(r["record"] == "checkpoint" for r in rows)
        print(f"{cfg}: {passed}/{total} checkpoints passed")


if __name__ == "__main__":
    main()
