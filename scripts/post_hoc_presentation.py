"""Baselines that show who wrote each entry and when (post hoc check, decision D27).

The baselines of the report hand the model the bare text of the entries. Here every entry gets a prefix
"[session N, <author>, <kind>] " when it is written to the system, so the prefix is part of the text that the
token limit, the ranking and the summary see. A calendar date does not exist on an entry, so the session number
is the time. Nothing in src/mam is changed: `mam.live.create` is replaced for the names ending in `_meta`.

  python scripts/post_hoc_presentation.py plan                 # list the 48 units, no model
  python scripts/post_hoc_presentation.py run [--max-cost-usd 1.5] [--max-minutes 25] [--workers 8]
"""
import argparse
import dataclasses
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import mam.live as live  # noqa: E402
from mam.run import plan_units, run_units  # noqa: E402
from mam.selection import select_live  # noqa: E402
from mam.systems import create as base_create  # noqa: E402

BASES = ["full_history", "sliding_window", "shared_rag_bm25", "rolling_summary"]
SYSTEMS = [f"{b}_meta" for b in BASES]
OUT = ROOT / "results/post_hoc/presentation"
DATA = ROOT / "data/eval"


def prefix(entry) -> str:
    return f"[session {entry.session}, {entry.author}, {entry.kind}] "


def make_create(llm):
    """A `create` for mam.live that understands the *_meta names; other names go to the original."""
    def create(name, **kw):
        if not name.endswith("_meta"):
            return base_create(name, **kw)
        base = name[: -len("_meta")]
        if base == "rolling_summary":
            kw = dict(kw, extractor="llm", llm=llm)
        system = base_create(base, **kw)
        original = system.write
        system.write = lambda entry: original(dataclasses.replace(entry, text=prefix(entry) + entry.text))
        return system
    return create


def scenario_ids() -> list[str]:
    ids = select_live(DATA / "manifest.json", "A")
    return [i for i in ids if i.startswith(("C1-", "C3-"))]


def units(repeats: int = 2):
    return plan_units(SYSTEMS, scenario_ids(), repeats)


def run(llm, out, **kw):
    live.create = make_create(llm)
    return run_units(units(), llm, DATA, out, **kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["plan", "run"])
    ap.add_argument("--max-cost-usd", type=float, default=1.5)
    ap.add_argument("--max-minutes", type=float, default=25)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    if a.cmd == "plan":
        us = units()
        print(len(us), "units;", ", ".join(scenario_ids()))
        return
    from mam.llm import ClaudeCliClient
    r = run(ClaudeCliClient(), OUT, workers=a.workers, max_minutes=a.max_minutes, max_cost_usd=a.max_cost_usd)
    print(f"done {r.done}, skipped {r.skipped}, failed {r.failed}, cost ${r.cost_usd:.3f}, stopped_by {r.stopped_by}")
    sys.exit(r.exit_code)


if __name__ == "__main__":
    main()
