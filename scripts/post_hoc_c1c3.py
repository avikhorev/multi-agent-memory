"""Post-hoc sensitivity analysis of the C1/C3 factor checkpoints (not pre-registered).

The primary result stays the strict rule of `mam.scoring.score_action`. This script only
reads the saved live units and the eval scenarios; it changes nothing and calls no model.

  python scripts/post_hoc_c1c3.py lenient          # counts under a lenient rule
  python scripts/post_hoc_c1c3.py blind            # write the shuffled, system-free answer sheet
  python scripts/post_hoc_c1c3.py join             # join the hand labels with the systems

Hand labels live in results/post_hoc/c1c3_labels.json as {"b01": "current", ...} with the
classes: current (asserts the current value), stale (asserts the stale value),
both (names both without deciding), absent (no value).
"""
import collections
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mam.scoring import normalize  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
UNITS = ROOT / "results/live/main/units"
OUT = ROOT / "results/post_hoc"
CLASSES = ("current", "stale", "both", "absent")
SYSTEMS = ["full_history", "ours", "rolling_summary", "shared_rag_bm25", "sliding_window"]


def rows():
    out = []
    for f in sorted(UNITS.glob("*.json")):
        d = json.loads(f.read_text())
        if d["scenario"][:2] not in ("C1", "C3"):
            continue
        sc = json.loads((ROOT / "data/eval" / f"{d['scenario']}.json").read_text())
        cps = {c["id"]: c for c in sc["checkpoints"]}
        for c in d["checkpoints"]:
            if not c.get("factor"):
                continue
            spec = cps[c["checkpoint"]]
            out.append({
                "system": d["system"], "scenario": d["scenario"], "repeat": d["repeat"],
                "checkpoint": c["checkpoint"], "question": spec["task_text"],
                "expect": spec["answer"].get("expect"), "stale": spec["answer"].get("stale", []),
                "disputed": spec["answer"].get("disputed", False),
                "answer": c["answer"], "strict": bool(c["passed"]), "label": c["label"],
            })
    return out


def lenient_ok(r):
    a = normalize(str(r["answer"]))
    return r["expect"] is not None and normalize(r["expect"]) in a


def cmd_lenient(rs):
    n, strict, len_ = collections.Counter(), collections.Counter(), collections.Counter()
    for r in rs:
        n[r["system"]] += 1
        strict[r["system"]] += r["strict"]
        len_[r["system"]] += lenient_ok(r)
    lines = ["| system | n | strict | lenient (expected value present, stale mention allowed) |", "|---|---|---|---|"]
    for s in SYSTEMS:
        lines.append(f"| {s} | {n[s]} | {strict[s]} | {len_[s]} |")
    fails = [r for r in rs if r["system"] != "ours" and not r["strict"]]
    with_value = [r for r in fails if lenient_ok(r)]
    lines.append("")
    lines.append(f"Baseline failures under the strict rule: {len(fails)}; of them the answer contains the expected value: {len(with_value)}.")
    text = "\n".join(lines) + "\n"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "c1c3_lenient.md").write_text(text)
    print(text)


def order(rs):
    idx = list(range(len(rs)))
    random.Random(20261031).shuffle(idx)
    return {f"b{k + 1:02d}": rs[i] for k, i in enumerate(idx)}


def cmd_blind(rs):
    items = order(rs)
    OUT.mkdir(parents=True, exist_ok=True)
    parts = ["# Blind answer sheet (system names hidden, fixed shuffle)\n"]
    for bid, r in items.items():
        parts.append(f"## {bid}\nQuestion: {r['question']}\nCurrent value: {r['expect']}\nStale values: {', '.join(r['stale']) or '-'}\nAnswer: {r['answer']}\n")
    (OUT / "c1c3_blind.md").write_text("\n".join(parts))
    print(len(items), "answers written")


def cmd_join(rs):
    items = order(rs)
    labels = json.loads((OUT / "c1c3_labels.json").read_text())
    assert set(labels) == set(items), "labels must cover every answer"
    assert set(labels.values()) <= set(CLASSES)
    table = collections.defaultdict(collections.Counter)
    lines = ["# Hand classification of the C1/C3 factor answers (author's judgement)\n",
             "Classes: current = asserts the current value; stale = asserts the stale value; both = names both without deciding; absent = no value.\n",
             "| id | system | scenario | repeat | strict | class | answer |", "|---|---|---|---|---|---|---|"]
    for bid, r in sorted(items.items(), key=lambda kv: (kv[1]["system"], kv[1]["scenario"], kv[1]["repeat"])):
        cls = labels[bid]
        table[r["system"]][cls] += 1
        ans = str(r["answer"]).replace("|", "/").replace("\n", " ")
        lines.append(f"| {bid} | {r['system']} | {r['scenario']} | {r['repeat']} | {'pass' if r['strict'] else 'fail'} | {cls} | {ans} |")
    summ = ["| system | current | stale | both | absent |", "|---|---|---|---|---|"]
    for s in SYSTEMS:
        summ.append(f"| {s} | " + " | ".join(str(table[s][c]) for c in CLASSES) + " |")
    text = "\n".join(summ) + "\n\n" + "\n".join(lines) + "\n"
    (OUT / "c1c3_classified.md").write_text(text)
    print("\n".join(summ))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    fn = {"lenient": cmd_lenient, "blind": cmd_blind, "join": cmd_join}.get(cmd)
    if not fn:
        sys.exit(__doc__)
    fn(rows())
