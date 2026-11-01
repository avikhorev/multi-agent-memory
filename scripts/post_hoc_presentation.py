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


# ---- analysis of the saved units (no model) -------------------------------------------------------------

import collections  # noqa: E402
import json  # noqa: E402
import random  # noqa: E402

from mam.scenario import load  # noqa: E402
from mam.scoring import normalize  # noqa: E402

MAIN = ROOT / "results/live/main/units"
CLASSES = ("current", "stale", "both", "absent")


def factor_rows(units_dir, rename=lambda n: n):
    rows = []
    for f in sorted(Path(units_dir).glob("*.json")):
        d = json.loads(f.read_text())
        if d["scenario"][:2] not in ("C1", "C3"):
            continue
        sc = load(DATA / f"{d['scenario']}.json")
        specs = {c.id: c for c in sc.checkpoints}
        for c in d["checkpoints"]:
            if c.get("factor"):
                spec = specs[c["checkpoint"]]
                rows.append({"system": rename(d["system"]), "scenario": d["scenario"], "repeat": d["repeat"],
                             "checkpoint": c["checkpoint"], "question": spec.task_text, "expect": spec.answer.expect,
                             "stale": list(spec.answer.stale), "answer": c["answer"], "strict": bool(c["passed"])})
    return rows


def lenient_ok(r):
    return r["expect"] is not None and normalize(r["expect"]) in normalize(str(r["answer"]))


def shuffled(rows):
    idx = list(range(len(rows)))
    random.Random(20261101).shuffle(idx)
    return {f"p{k + 1:02d}": rows[i] for k, i in enumerate(idx)}


def analyze(cmd):
    pres = factor_rows(OUT / "units")
    out = OUT
    if cmd == "counts":
        main = [r for r in factor_rows(MAIN) if r["system"] in BASES + ["ours"]]
        lines = ["| system | strict | lenient | n |", "|---|---|---|---|"]
        for label, rs in (("plain baselines, committed run (2 repeats)", main), ("with prefix, this check (2 repeats)", pres)):
            lines.append(f"| **{label}** | | | |")
            names = BASES + (["ours"] if rs is main else [])
            for b in names:
                sel = [r for r in rs if r["system"] in (b, f"{b}_meta")]
                lines.append(f"| {b} | {sum(r['strict'] for r in sel)} | {sum(lenient_ok(r) for r in sel)} | {len(sel)} |")
        text = "\n".join(lines) + "\n"
        (out / "counts.md").write_text(text)
        print(text)
    elif cmd == "blind":
        items = shuffled(pres)
        parts = ["# Blind answer sheet of the presentation check (system names hidden, fixed shuffle)\n"]
        for bid, r in items.items():
            parts.append(f"## {bid}\nQuestion: {r['question']}\nCurrent value: {r['expect']}\nStale values: {', '.join(r['stale']) or '-'}\nAnswer: {r['answer']}\n")
        (out / "blind.md").write_text("\n".join(parts))
        print(len(items), "answers")
    elif cmd == "join":
        items = shuffled(pres)
        labels = json.loads((out / "labels.json").read_text())
        assert set(labels) == set(items) and set(labels.values()) <= set(CLASSES)
        table = collections.defaultdict(collections.Counter)
        rows = ["| id | system | scenario | repeat | strict | class | answer |", "|---|---|---|---|---|---|---|"]
        for bid, r in sorted(items.items(), key=lambda kv: (kv[1]["system"], kv[1]["scenario"], kv[1]["repeat"])):
            table[r["system"]][labels[bid]] += 1
            rows.append(f"| {bid} | {r['system']} | {r['scenario']} | {r['repeat']} | {'pass' if r['strict'] else 'fail'} | {labels[bid]} | {str(r['answer']).replace('|', '/')} |")
        summ = ["| system | current | stale | both | absent |", "|---|---|---|---|---|"]
        for b in SYSTEMS:
            summ.append(f"| {b} | " + " | ".join(str(table[b][c]) for c in CLASSES) + " |")
        text = ("# Hand classification of the answers with prefix (the labeller is the agent)\n\n" + "\n".join(summ)
                + "\n\n" + "\n".join(rows) + "\n")
        (out / "classified.md").write_text(text)
        print("\n".join(summ))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["plan", "run", "counts", "blind", "join"])
    ap.add_argument("--max-cost-usd", type=float, default=1.5)
    ap.add_argument("--max-minutes", type=float, default=25)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    if a.cmd in ("counts", "blind", "join"):
        analyze(a.cmd)
        return
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
