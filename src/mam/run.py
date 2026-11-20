"""Resumable run of live units and printing of traces.

A unit is a triple (system, scenario, repeat). Its result is written atomically to one file; a finished
unit is skipped on the next run. New units do not start after the time or cost limit;
rate limits that do not clear stop the run with their own exit code, so that it can be
continued later. There are no repository operations here.

  python -m mam.run live --split dev --select smoke --systems ours,full_history --out results/live/smoke
  python -m mam.run trace C1-dev-0100 --dir results/live/smoke
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

from mam.live import run_live
from mam.llm import MODEL, PINNED_CLI_VERSION, ClaudeCliClient, RateLimitTimeout
from mam.scenario import load
from mam.selection import select_live

# Exit codes: done; stopped by a limit or there were failures; rate limit (EX_TEMPFAIL).
EXIT_OK, EXIT_INCOMPLETE, EXIT_RATE_LIMITED = 0, 2, 75


class Unit(NamedTuple):
    """Unit of work."""
    system: str  # name of the memory system
    scenario: str  # scenario id
    repeat: int  # repeat number (the model is nondeterministic, so runs are repeated)


@dataclass
class Report:
    """Result of the run."""
    done: int = 0  # done in this run
    skipped: int = 0  # skipped as finished
    failed: int = 0  # failed (will be retried on the next run)
    cost_usd: float = 0.0  # spent, including previous runs
    stopped_by: str | None = None  # time | cost | rate_limit | None
    exit_code: int = EXIT_OK  # process exit code


def plan_units(systems: list[str], scenarios: list[str], repeats: int) -> list[Unit]:
    """All combinations. The repeat is the outer loop: when stopped by a limit, all systems get through at least the first repeat."""
    return [Unit(sy, sc, r) for r in range(repeats) for sc in scenarios for sy in systems]


def _name(u: Unit) -> str:
    """File name of the unit (and of its trace)."""
    return f"{u.system}__{u.scenario}__r{u.repeat}"


def _commit() -> str:
    """Code commit for the result manifest: from MAM_COMMIT (there is no git in the container) or from git; otherwise "unknown"."""
    if os.environ.get("MAM_COMMIT"):
        return os.environ["MAM_COMMIT"]
    try:
        p = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10)
        return p.stdout.strip() if p.returncode == 0 and p.stdout.strip() else "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _write_atomic(path: Path, text: str) -> None:
    """We write to a temporary file and rename it: if interrupted, no half-written file remains."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _spent(units_dir: Path) -> float:
    """How much has already been spent by finished units (included in the cost limit)."""
    total = 0.0
    for f in units_dir.glob("*.json"):
        total += float(json.loads(f.read_text(encoding="utf-8")).get("cost_usd") or 0)
    return total


def run_units(units: list[Unit], llm, data_dir, out_dir, *, workers: int = 8, max_minutes: float | None = None,
              max_cost_usd: float = 10.0, now=time.monotonic, limit: int = 2000, attempts: int = 2) -> Report:
    """Runs the units in parallel; attempts — tries per unit before a failure is recognized; now is replaced in tests."""
    out, data = Path(out_dir), Path(data_dir)
    (out / "units").mkdir(parents=True, exist_ok=True)
    (out / "traces").mkdir(exist_ok=True)
    report = Report(cost_usd=_spent(out / "units"))
    commit, started_at = _commit(), now()  # for the manifest and the time-limit clock
    deadline = None if max_minutes is None else started_at + max_minutes * 60
    lock, state = threading.Lock(), {"stop": None}  # lock for shared counters; the reason for stopping

    def work(u: Unit) -> None:
        scenario = load(data / f"{u.scenario}.json")
        last: Exception | None = None
        for _ in range(attempts):
            try:
                t0 = datetime.now(timezone.utc)
                res = run_live(scenario, u.system, llm, repeat=u.repeat, limit=limit)
                break
            except RateLimitTimeout:
                with lock:
                    state["stop"] = "rate_limit"
                raise
            except Exception as err:  # the unit stays unfinished and will be repeated on the next run
                last = err
        else:
            with lock:
                report.failed += 1
                with open(out / "failures.log", "a", encoding="utf-8") as f:
                    f.write(f"{_name(u)}: {type(last).__name__}: {str(last)[:200]}\n")
            return
        # The trace goes to a separate file, so that the unit's file stays compact.
        trace = res.pop("trace")
        res["cost_usd"] = res["totals"]["cost_usd"]
        # Manifest: how the result was obtained (model, CLI version, commit, time) — for reproducibility.
        res["manifest"] = {"system": u.system, "scenario": u.scenario, "repeat": u.repeat, "model": MODEL,
                           "cli_version": PINNED_CLI_VERSION, "commit": commit,
                           "api_key_set": bool(os.environ.get("ANTHROPIC_API_KEY")),
                           "started": t0.isoformat(), "finished": datetime.now(timezone.utc).isoformat()}
        # The unit is written last: its presence means "done", and the trace is already there by then.
        _write_atomic(out / "traces" / f"{_name(u)}.jsonl", "".join(json.dumps(t, sort_keys=True) + "\n" for t in trace))
        _write_atomic(out / "units" / f"{_name(u)}.json", json.dumps(res, sort_keys=True, indent=1))
        with lock:
            report.done += 1
            report.cost_usd += res["cost_usd"]

    pending = set()  # started but not finished tasks
    with ThreadPoolExecutor(workers) as pool:
        for u in units:
            if (out / "units" / f"{_name(u)}.json").exists():
                report.skipped += 1
                continue
            # We do not start more than workers tasks at once, so that the limits are checked on fresh data.
            while len(pending) >= workers:
                finished, pending = wait(pending, return_when=FIRST_COMPLETED)
            with lock:
                # We estimate the cost of the running ones by the average of the finished ones: we stop before exceeding, not after.
                avg = report.cost_usd / report.done if report.done else 0.0
                if state["stop"] is None and deadline is not None and now() >= deadline:
                    state["stop"] = "time"
                if state["stop"] is None and report.cost_usd + avg * len(pending) >= max_cost_usd:
                    state["stop"] = "cost"
            if state["stop"]:
                break
            pending.add(pool.submit(work, u))
        for fut in pending:
            try:
                fut.result()
            except RateLimitTimeout:
                state["stop"] = "rate_limit"
    report.stopped_by = state["stop"]
    if state["stop"] == "rate_limit":
        report.exit_code = EXIT_RATE_LIMITED
    elif state["stop"] or report.failed:
        report.exit_code = EXIT_INCOMPLETE
    # The log of rate-limit waits goes to a separate file, so as not to mix it with the results.
    if getattr(llm, "infra_log", None):
        with open(out / "infra.log.jsonl", "a", encoding="utf-8") as f:
            f.write("".join(json.dumps(e) + "\n" for e in llm.infra_log))
    return report


def trace_lines(out_dir, scenario: str):
    """Trace lines of all units of the scenario, each with an added unit field."""
    for f in sorted((Path(out_dir) / "traces").glob(f"*__{scenario}__r*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            yield json.dumps(dict(json.loads(line), unit=f.stem), sort_keys=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    lv = sub.add_parser("live")
    lv.add_argument("--split", required=True, choices=["dev", "eval"])
    lv.add_argument("--select", choices=["smoke", "A", "B"])
    lv.add_argument("--scenarios", default=None, help="comma-separated ids, instead of --select")
    lv.add_argument("--systems", default="ours,full_history,sliding_window,rolling_summary,shared_rag_bm25")
    lv.add_argument("--repeats", type=int, default=1)
    lv.add_argument("--workers", type=int, default=8)
    lv.add_argument("--out", required=True)
    lv.add_argument("--max-minutes", type=float, default=None)
    lv.add_argument("--max-cost-usd", type=float, default=10.0)
    lv.add_argument("--limit", type=int, default=2000)
    tr = sub.add_parser("trace")
    tr.add_argument("scenario")
    tr.add_argument("--dir", required=True)
    a = ap.parse_args()
    if a.cmd == "trace":
        for line in trace_lines(a.dir, a.scenario):
            print(line)
        return
    data = Path(f"data/{a.split}")
    ids = a.scenarios.split(",") if a.scenarios else select_live(data / "manifest.json", a.select or "smoke")
    units = plan_units(a.systems.split(","), ids, a.repeats)
    print(f"model {MODEL}, cli {PINNED_CLI_VERSION}, api_key_set {bool(os.environ.get('ANTHROPIC_API_KEY'))}, "
          f"units {len(units)}, workers {a.workers}", flush=True)
    report = run_units(units, ClaudeCliClient(), data, a.out, workers=a.workers, max_minutes=a.max_minutes,
                       max_cost_usd=a.max_cost_usd, limit=a.limit)
    print(f"done {report.done}, skipped {report.skipped}, failed {report.failed}, cost ${report.cost_usd:.3f}, "
          f"stopped_by {report.stopped_by}", flush=True)
    sys.exit(report.exit_code)


if __name__ == "__main__":
    main()
