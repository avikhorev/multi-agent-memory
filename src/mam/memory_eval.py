"""Memory-level evaluation: replay scenarios through a memory system, score the contexts built at checkpoints.

No model is called. Results are deterministic; timings (which are not) go to <out>/timing/.

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

ABLATIONS = {"no_validity": "validity", "no_scopes": "scopes", "no_trust": "trust",
             "no_pinned_constraints": "pinned_constraints"}
DEFAULT_SYSTEMS = (
    ["full_history", "sliding_window", "shared_rag_bm25", "rolling_summary@rules", "ours@oracle", "ours@rules"]
    + [f"ours@oracle-{a}" for a in ABLATIONS])


def make_system(cfg: str, limit: int = 2000, cache_path=None):
    """cfg: name, name@extractor or name@extractor-ablation."""
    name, _, rest = cfg.partition("@")
    extractor, _, ablation = rest.partition("-")
    kwargs = {"limit": limit}
    if extractor:
        kwargs.update(extractor=extractor, cache_path=cache_path if extractor == "cache" else None)
    if ablation:
        kwargs["ablate"] = {ABLATIONS[ablation]}
    return create(name, **kwargs)


def run_scenario(cfg: str, scenario, limit: int = 2000, cache_path=None):
    system = make_system(cfg, limit, cache_path)
    by_session: dict[int, list] = {}
    for e in entries(scenario):
        by_session.setdefault(e.session, []).append(e)
    records, t_write, t_read = [], 0.0, 0.0
    for k in range(1, scenario.n_sessions + 1):
        for cp in (c for c in scenario.checkpoints if c.session == k):
            reader = Reader(role=cp.role, task_id=f"task-{scenario.id}", session=k, query=cp.task_text)
            t0 = time.perf_counter()
            try:
                ctx = system.context(reader)
                res = score_context(scenario, cp.id, ctx)
                rec = {"passed": res.passed, "violations": res.violations, "stale_present": res.stale_present,
                       "foreign_private_present": res.foreign_private_present,
                       "attack_in_instruction_slot": res.attack_in_instruction_slot, "token_count": ctx.token_count}
            except ValueError as err:  # e.g. pinned constraints do not fit the limit
                rec = {"passed": False, "violations": [f"context error: {err}"], "stale_present": False,
                       "foreign_private_present": False, "attack_in_instruction_slot": False, "token_count": 0}
            t_read += time.perf_counter() - t0
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
    summary = {"record": "scenario", "system": cfg, "scenario": scenario.id, "category": scenario.category,
               "quarantined": len(getattr(system, "quarantined", [])), "refusals": len(getattr(system, "refusals", []))}
    return records + [summary], {"system": cfg, "scenario": scenario.id, "write_ms": round(t_write * 1000, 2),
                                 "read_ms": round(t_read * 1000, 2)}


def scenario_paths(data_dir: Path) -> list[Path]:
    manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
    return [data_dir / f"{s['id']}.json" for s in manifest["scenarios"]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True, choices=["dev", "eval", "holdout"])
    ap.add_argument("--data", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--systems", default=",".join(DEFAULT_SYSTEMS))
    ap.add_argument("--limit", type=int, default=2000)
    ap.add_argument("--cache", default=None)
    a = ap.parse_args()
    data_dir = Path(a.data or ("holdout" if a.split == "holdout" else f"data/{a.split}"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    scenarios = [load(p) for p in scenario_paths(data_dir)]
    for cfg in a.systems.split(","):
        rows, timing = [], []
        for s in scenarios:
            recs, tm = run_scenario(cfg, s, a.limit, a.cache)
            rows += recs
            timing.append(tm)
        (out / f"{cfg}.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
        (out / "timing").mkdir(exist_ok=True)
        (out / "timing" / f"{cfg}.jsonl").write_text("".join(json.dumps(t, sort_keys=True) + "\n" for t in timing), encoding="utf-8")
        passed = sum(r["passed"] for r in rows if r["record"] == "checkpoint")
        total = sum(r["record"] == "checkpoint" for r in rows)
        print(f"{cfg}: {passed}/{total} checkpoints passed")


if __name__ == "__main__":
    main()
