"""The extraction pass: the model reads each source entry once and writes each session summary once;
the answers are saved and later replayed without the model (the 'cache' extractor, the 'cache' summary).
So the expensive model call is made once, and all system comparisons afterwards run on the saved answers.

The unit of work is a scenario. Its lines are written to one file atomically; finished scenarios are skipped
on the next run (the pass can be interrupted and resumed). New scenarios do not start after the time limit or the
cost limit; rate limits that do not clear stop the pass with their own exit code. Lines
are saved even if the model refused: the refusal is written as a missing fact (or summary) and counted separately.

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

# Exit codes: all done; stopped by a limit or there were failures; hit a rate limit (EX_TEMPFAIL).
EXIT_OK, EXIT_INCOMPLETE, EXIT_RATE_LIMITED = 0, 2, 75


@dataclass
class Pass:
    """Result of the extraction pass."""
    done: int = 0  # scenarios processed in this run
    skipped: int = 0  # skipped as already finished
    failed: int = 0  # failed with an error (will be retried on the next run)
    refusals: int = 0  # total model refusals
    entry_refusals: int = 0  # of which during fact extraction from entries
    summary_refusals: int = 0  # of which during summary writing
    cost_usd: float = 0.0  # spent, including previous runs
    stopped_by: str | None = None  # time | cost | rate_limit | None
    exit_code: int = EXIT_OK  # process exit code


def _write_atomic(path: Path, text: str) -> None:
    """We write to a temporary file and rename it: if interrupted, no half-written file remains."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def extract_scenario(scenario, llm, limit: int = 2000) -> tuple[list[dict], dict]:
    """Runs the scenario through the structured memory and the summary, saving the model's answers.
    Returns (cache lines, statistics)."""
    memory = Ours(limit, extractor="llm", llm=llm)  # provides fact extractions
    summary = LLMSummary(limit, llm)  # provides session summaries
    all_entries = entries(scenario)
    by_id = {e.id: e for e in all_entries}  # to find an entry by its id and apply the constraint rule
    task_id = f"task-{scenario.id}"
    rows: list[dict] = []
    cost = 0.0
    for k in range(1, scenario.n_sessions + 1):
        for e in (x for x in all_entries if x.session == k):
            memory.write(e)
            summary.write(e)
        memory.end_session(k)
        summary.end_session(k)
        # The cost is counted over all calls of this session.
        cost += sum(out.usage.cost_usd for _, out in memory.drain_llm_calls() + summary.drain_llm_calls())
        for rec in memory.drain_extractions():
            rows.append({"kind": "entry", "scenario": scenario.id, "task_id": task_id, "entry_id": rec["entry_id"],
                         "session": rec["session"], "refusal": rec["refused"],
                         # Constraints are not from the model but come from the rule — as in the live system.
                         "constraints": list(rule_constraints(by_id[rec["entry_id"]])),
                         "facts": [{"entity": f["entity"], "attribute": f["attribute"], "value": f["value"],
                                    "event_time": f["valid_from"], "source": f["source"]} for f in rec["facts"]]})
        refused = k in summary.refusals  # refusal on the summary: store an empty text with a flag
        rows.append({"kind": "summary", "scenario": scenario.id, "task_id": task_id, "session": k,
                     "text": "" if refused else summary.summary_text, "refusal": refused})
    stats = {"cost_usd": round(cost, 6), "entry_refusals": sum(r["refusal"] for r in rows if r["kind"] == "entry"),
             "summary_refusals": sum(r["refusal"] for r in rows if r["kind"] == "summary"), "rows": len(rows)}
    return rows, stats


def run_pass(ids: list[str], llm, data_dir, out_dir, *, workers: int = 8, max_minutes: float | None = None,
             max_cost_usd: float = 10.0, now=time.monotonic, limit: int = 2000) -> Pass:
    """Processes the scenarios ids in parallel. now is replaced in tests to check the time limit."""
    out, data = Path(out_dir), Path(data_dir)
    (out / "scenarios").mkdir(parents=True, exist_ok=True)
    report = Pass()
    # What has already been spent in previous runs is included in the cost limit.
    for meta in (out / "scenarios").glob("*.meta.json"):
        report.cost_usd += json.loads(meta.read_text())["cost_usd"]
    deadline = None if max_minutes is None else now() + max_minutes * 60
    lock, state = threading.Lock(), {"stop": None}  # lock for shared counters; the reason for stopping

    def work(sid: str) -> None:
        try:
            rows, stats = extract_scenario(load(data / f"{sid}.json"), llm, limit)
        except RateLimitTimeout:
            with lock:
                state["stop"] = "rate_limit"
            raise
        except Exception as err:  # the scenario stays unfinished and will be repeated on the next run
            with lock:
                report.failed += 1
                with open(out / "failures.log", "a", encoding="utf-8") as f:
                    f.write(f"{sid}: {type(err).__name__}: {str(err)[:200]}\n")
            return
        # First the meta, then the lines: the presence of the .jsonl means "scenario ready", and the meta is already there by then.
        _write_atomic(out / "scenarios" / f"{sid}.meta.json", json.dumps(stats, sort_keys=True))
        _write_atomic(out / "scenarios" / f"{sid}.jsonl", "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
        with lock:
            report.done += 1
            report.cost_usd += stats["cost_usd"]
            report.entry_refusals += stats["entry_refusals"]
            report.summary_refusals += stats["summary_refusals"]
            report.refusals += stats["entry_refusals"] + stats["summary_refusals"]

    pending = set()  # started but not finished tasks
    with ThreadPoolExecutor(workers) as pool:
        for sid in ids:
            if (out / "scenarios" / f"{sid}.jsonl").exists():
                report.skipped += 1
                continue
            # We do not start more than workers tasks at once, so that the limits are checked on fresh data.
            while len(pending) >= workers:
                _, pending = wait(pending, return_when=FIRST_COMPLETED)
            with lock:
                # We estimate the cost of the running ones by the average of the finished ones: we stop before exceeding, not after.
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
    """Collects the scenario files into one cache file, in the order of scenario ids (inside a scenario the order of lines is kept)."""
    files = sorted((Path(out_dir) / "scenarios").glob("*.jsonl"))
    lines = [ln for f in files for ln in f.read_text(encoding="utf-8").splitlines() if ln.strip()]
    _write_atomic(Path(target), "".join(ln + "\n" for ln in lines))
    return len(lines)


def select_ids(manifest_path, select: str) -> list[str]:
    """all — all scenarios of the manifest; trial — the first five of each category (a cheap trial)."""
    scenarios = json.load(open(manifest_path))["scenarios"]
    if select == "all":
        return [s["id"] for s in scenarios]
    per: dict[str, int] = {}
    ids = []
    for s in scenarios:  # trial: the first five scenarios of each category
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
