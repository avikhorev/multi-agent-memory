"""The extraction pass: the model reads every source entry and writes every session summary once; the
answers are saved and replayed later without a model (extractor 'cache', rolling summary 'cache').

A scenario is the unit of work. Its rows go to one file, written atomically; finished scenarios are
skipped on the next start. New scenarios stop at the time or cost limit; rate limits that do not clear stop
the pass with its own exit code. Rows are saved even if the model refused: a refusal is kept as a missing
fact (or a missing summary) and counted apart.

  python -m mam.extraction run --split dev --select trial --out results/extraction/dev
  python -m mam.extraction merge --in results/extraction/dev --out results/extraction/dev/cache.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path

from mam.extract import rule_constraints
from mam.llm import ClaudeCliClient, RateLimitTimeout
from mam.scenario import load
from mam.simulate import entries
from mam.systems.ours import Ours
from mam.systems.summary import LLMSummary

EXIT_OK, EXIT_INCOMPLETE, EXIT_RATE_LIMITED = 0, 2, 75


@dataclass
class Pass:
    done: int = 0
    skipped: int = 0
    failed: int = 0
    refusals: int = 0
    entry_refusals: int = 0
    summary_refusals: int = 0
    cost_usd: float = 0.0
    stopped_by: str | None = None
    exit_code: int = EXIT_OK


def _write_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def extract_scenario(scenario, llm, limit: int = 2000) -> tuple[list[dict], dict]:
    """Replay a scenario through the structured memory and the summary, saving what the model answered."""
    memory = Ours(limit, extractor="llm", llm=llm)
    summary = LLMSummary(limit, llm)
    all_entries = entries(scenario)
    by_id = {e.id: e for e in all_entries}
    task_id = f"task-{scenario.id}"
    rows: list[dict] = []
    cost = 0.0
    for k in range(1, scenario.n_sessions + 1):
        for e in (x for x in all_entries if x.session == k):
            memory.write(e)
            summary.write(e)
        memory.end_session(k)
        summary.end_session(k)
        cost += sum(out.usage.cost_usd for _, out in memory.drain_llm_calls() + summary.drain_llm_calls())
        for rec in memory.drain_extractions():
            rows.append({"kind": "entry", "scenario": scenario.id, "task_id": task_id, "entry_id": rec["entry_id"],
                         "session": rec["session"], "refusal": rec["refused"],
                         "constraints": list(rule_constraints(by_id[rec["entry_id"]])),
                         "facts": [{"entity": f["entity"], "attribute": f["attribute"], "value": f["value"],
                                    "event_time": f["valid_from"], "source": f["source"]} for f in rec["facts"]]})
        refused = k in summary.refusals
        rows.append({"kind": "summary", "scenario": scenario.id, "task_id": task_id, "session": k,
                     "text": "" if refused else summary.summary_text, "refusal": refused})
    stats = {"cost_usd": round(cost, 6), "entry_refusals": sum(r["refusal"] for r in rows if r["kind"] == "entry"),
             "summary_refusals": sum(r["refusal"] for r in rows if r["kind"] == "summary"), "rows": len(rows)}
    return rows, stats


def run_pass(ids: list[str], llm, data_dir, out_dir, *, workers: int = 8, max_minutes: float | None = None,
             max_cost_usd: float = 10.0, now=time.monotonic, limit: int = 2000) -> Pass:
    out, data = Path(out_dir), Path(data_dir)
    (out / "scenarios").mkdir(parents=True, exist_ok=True)
    report = Pass()
    for meta in (out / "scenarios").glob("*.meta.json"):
        report.cost_usd += json.loads(meta.read_text())["cost_usd"]
    deadline = None if max_minutes is None else now() + max_minutes * 60
    lock, state = threading.Lock(), {"stop": None}

    def work(sid: str) -> None:
        try:
            rows, stats = extract_scenario(load(data / f"{sid}.json"), llm, limit)
        except RateLimitTimeout:
            with lock:
                state["stop"] = "rate_limit"
            raise
        except Exception as err:  # left undone, retried on the next start
            with lock:
                report.failed += 1
                with open(out / "failures.log", "a", encoding="utf-8") as f:
                    f.write(f"{sid}: {type(err).__name__}: {str(err)[:200]}\n")
            return
        _write_atomic(out / "scenarios" / f"{sid}.meta.json", json.dumps(stats, sort_keys=True))
        _write_atomic(out / "scenarios" / f"{sid}.jsonl", "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
        with lock:
            report.done += 1
            report.cost_usd += stats["cost_usd"]
            report.entry_refusals += stats["entry_refusals"]
            report.summary_refusals += stats["summary_refusals"]
            report.refusals += stats["entry_refusals"] + stats["summary_refusals"]

    pending = set()
    with ThreadPoolExecutor(workers) as pool:
        for sid in ids:
            if (out / "scenarios" / f"{sid}.jsonl").exists():
                report.skipped += 1
                continue
            while len(pending) >= workers:
                _, pending = wait(pending, return_when=FIRST_COMPLETED)
            with lock:
                avg = report.cost_usd / report.done if report.done else 0.0
                if state["stop"] is None and deadline is not None and now() >= deadline:
                    state["stop"] = "time"
                if state["stop"] is None and report.cost_usd + avg * len(pending) >= max_cost_usd:
                    state["stop"] = "cost"
            if state["stop"]:
                break
            pending.add(pool.submit(work, sid))
        for fut in pending:
            try:
                fut.result()
            except RateLimitTimeout:
                state["stop"] = "rate_limit"
    report.stopped_by = state["stop"]
    report.exit_code = (EXIT_RATE_LIMITED if state["stop"] == "rate_limit"
                        else EXIT_INCOMPLETE if state["stop"] or report.failed else EXIT_OK)
    return report


def merge_rows(out_dir, target) -> int:
    """All scenario files into one cache file, ordered by scenario id (rows keep their order inside a scenario)."""
    files = sorted((Path(out_dir) / "scenarios").glob("*.jsonl"))
    lines = [ln for f in files for ln in f.read_text(encoding="utf-8").splitlines() if ln.strip()]
    _write_atomic(Path(target), "".join(ln + "\n" for ln in lines))
    return len(lines)


def select_ids(manifest_path, select: str) -> list[str]:
    scenarios = json.load(open(manifest_path))["scenarios"]
    if select == "all":
        return [s["id"] for s in scenarios]
    per: dict[str, int] = {}
    ids = []
    for s in scenarios:  # trial: the first five scenarios of every category
        if per.get(s["category"], 0) < 5:
            per[s["category"]] = per.get(s["category"], 0) + 1
            ids.append(s["id"])
    return ids


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--split", required=True, choices=["dev", "eval", "holdout"])
    r.add_argument("--select", default="all", choices=["trial", "all"])
    r.add_argument("--out", required=True)
    r.add_argument("--workers", type=int, default=8)
    r.add_argument("--max-minutes", type=float, default=None)
    r.add_argument("--max-cost-usd", type=float, default=10.0)
    m = sub.add_parser("merge")
    m.add_argument("--in", dest="src", required=True)
    m.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "merge":
        print(f"{merge_rows(a.src, a.out)} rows")
        return
    data = Path("holdout" if a.split == "holdout" else f"data/{a.split}")
    ids = select_ids(data / "manifest.json", a.select)
    print(f"scenarios {len(ids)}, workers {a.workers}, api_key_set {bool(os.environ.get('ANTHROPIC_API_KEY'))}", flush=True)
    rep = run_pass(ids, ClaudeCliClient(), data, a.out, workers=a.workers, max_minutes=a.max_minutes,
                   max_cost_usd=a.max_cost_usd)
    print(f"done {rep.done}, skipped {rep.skipped}, failed {rep.failed}, refusals {rep.refusals} "
          f"(entries {rep.entry_refusals}, summaries {rep.summary_refusals}), cost ${rep.cost_usd:.3f}, "
          f"stopped_by {rep.stopped_by}", flush=True)
    sys.exit(rep.exit_code)


if __name__ == "__main__":
    main()
