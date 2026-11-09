"""Baselines that show who wrote each entry and when (post hoc check, decision D27).

The baselines of the report hand the model the bare text of the entries. Here every entry gets a prefix
"[session N, <author>, <kind>] " when it is written to the system, so the prefix is part of the text that the
token limit, the ranking and the summary see. A calendar date does not exist on an entry, so the session number
is the time. Nothing in src/mam is changed: `mam.live.create` is replaced for the names ending in `_meta`.

  python experiments/post_hoc_presentation.py plan                 # list the 48 units, no model
  python experiments/post_hoc_presentation.py run [--max-cost-usd 1.5] [--max-minutes 25] [--workers 8]
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


CONTROL = ROOT / "results/live/control"


def all_checks(units_dir, repeats=None):
    """Passed checks on all checkpoints of the C1 and C3 scenarios, per system and repeat."""
    out = collections.defaultdict(collections.Counter)  # (system, repeat) -> ok / n
    for f in sorted(Path(units_dir).glob("*.json")):
        d = json.loads(f.read_text())
        if d["scenario"][:2] not in ("C1", "C3") or (repeats is not None and d["repeat"] not in repeats):
            continue
        name = d["system"][: -len("_meta")] if d["system"].endswith("_meta") else d["system"]
        for c in d["checkpoints"]:
            out[(name, d["repeat"])]["n"] += 1
            out[(name, d["repeat"])]["ok"] += c["label"] == "ok"
            if not c["factor"]:
                out[(name, d["repeat"])]["nf_n"] += 1
                out[(name, d["repeat"])]["nf_ok"] += c["label"] == "ok"
                out[(name, d["repeat"])]["nf_memory"] += c["label"] == "memory"
    return out


def read_stats(units_dir, system, prefix_scenarios=("C1",)):
    """Mean number of context items and tokens per memory read of one system on the given categories."""
    items, toks = [], []
    for f in sorted(Path(units_dir).glob(f"{system}__*.jsonl" if False else "*.json")):
        d = json.loads(f.read_text())
        if d["system"] != system or d["scenario"][:2] not in prefix_scenarios:
            continue
        tf = Path(units_dir).parent / "traces" / f"{f.stem}.jsonl"
        for line in tf.read_text().splitlines():
            t = json.loads(line)
            if t["op"] == "read":
                items.append(len(t["item_ids"]))
                toks.append(t["token_count"])
    return (sum(items) / len(items), sum(toks) / len(toks), len(items)) if items else (0, 0, 0)


def analyze_all():
    lines = ["", "## All checkpoints of the C1 and C3 scenarios (48 per system; supplement, not part of the D27 criterion)", "",
             "| system | without prefix | with prefix | difference |", "|---|---|---|---|"]
    main = all_checks(MAIN)
    pres = all_checks(OUT / "units")
    for b in BASES + ["ours"]:
        a = sum(main[(b, r)]["ok"] for r in (0, 1))
        n = sum(main[(b, r)]["n"] for r in (0, 1))
        if b == "ours":
            lines.append(f"| ours (not rerun) | {a}/{n} | | |")
            continue
        p = sum(pres[(b, r)]["ok"] for r in (0, 1))
        lines.append(f"| {b} | {a}/{n} | {p}/{sum(pres[(b, r)]['n'] for r in (0, 1))} | {p - a:+d} |")
    ctrl = all_checks(CONTROL / "units", repeats={0})
    lines += ["", "Run-to-run spread on the 24 checks of one run (repeat 0 and repeat 1 of the main run, control run):", "",
              "| system | main r0 | main r1 | control | min-max |", "|---|---|---|---|---|"]
    for b in BASES + ["ours"]:
        v = [main[(b, 0)]["ok"], main[(b, 1)]["ok"], ctrl[(b, 0)]["ok"]]
        lines.append(f"| {b} | {v[0]} | {v[1]} | {v[2]} | {min(v)}-{max(v)} |")
    lines += ["", "Non-factor checkpoints (36 per system over both repeats), ok and label memory:", "",
              "| system | ok without prefix | ok with prefix | memory label without prefix | memory label with prefix |", "|---|---|---|---|---|"]
    for b in BASES:
        g = lambda d: (sum(d[(b, r)]["nf_ok"] for r in (0, 1)), sum(d[(b, r)]["nf_memory"] for r in (0, 1)), sum(d[(b, r)]["nf_n"] for r in (0, 1)))
        (ao, am, an), (po, pm, pn) = g(main), g(pres)
        lines.append(f"| {b} | {ao}/{an} | {po}/{pn} | {am} | {pm} |")
    lines += ["", "Sliding window on C1 scenarios: mean context items and tokens per memory read:", "",
              "| variant | items | tokens | reads |", "|---|---|---|---|"]
    for label, d, name in (("plain, main run", MAIN, "sliding_window"), ("plain, control run", CONTROL / "units", "sliding_window"),
                           ("with prefix", OUT / "units", "sliding_window_meta")):
        i, t, n = read_stats(d, name)
        lines.append(f"| {label} | {i:.1f} | {t:.0f} | {n} |")
    return "\n".join(lines) + "\n"


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
        text = "\n".join(lines) + "\n" + analyze_all()
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
