"""Compare a control repeat of the live run with the committed run, side by side (post hoc).

  python scripts/post_hoc_control_repeat.py [--main results/live/main] [--control results/live/control]
                                             [--out results/post_hoc/control_repeat.md]

Both sides use repeat 0 only (the control has one repeat), so the units are like for like.
Nothing is selected: every table of the report that the live units can rebuild is shown.
One repeat gives no intervals; this is a comparison of two runs, not a statistical test.
"""
import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mam.live import session_source  # noqa: E402
from mam.live_tables import category, n_sessions, selected  # noqa: E402
from mam.scenario import load  # noqa: E402
from mam.scoring import normalize  # noqa: E402

SYSTEMS = ["full_history", "ours", "rolling_summary", "shared_rag_bm25", "sliding_window"]
CATS = ["C0", "C1", "C2", "C3", "C4", "C5", "C6"]


def load_units(d):
    out = []
    for f in sorted((Path(d) / "units").glob("*.json")):
        u = json.loads(f.read_text())
        if u["repeat"] == 0:
            out.append(u)
    return out


def trace(d, u):
    f = Path(d) / "traces" / f"{u['system']}__{u['scenario']}__r{u['repeat']}.jsonl"
    return [json.loads(x) for x in f.read_text().splitlines() if x.strip()] if f.exists() else []


def lenient(u, c):
    sc = load(ROOT / "data/eval" / f"{u['scenario']}.json")
    spec = next(x for x in sc.checkpoints if x.id == c["checkpoint"])
    return spec.answer.expect is not None and normalize(spec.answer.expect) in normalize(str(c["answer"]))


def metrics(d):
    us = load_units(d)
    m = collections.defaultdict(collections.Counter)  # (system) -> counter
    cat_ok = collections.defaultdict(collections.Counter)
    cat_n = collections.defaultdict(collections.Counter)
    tok = collections.defaultdict(lambda: collections.defaultdict(list))
    for u in us:
        s, cat = u["system"], category(u)
        m[s]["units"] += 1
        m[s]["cost"] += u["cost_usd"]
        for c in selected(u):
            cat_n[(cat, s)]["n"] += 1
            cat_ok[(cat, s)]["ok"] += c["label"] == "ok"
        for c in u["checkpoints"]:
            m[s]["all_n"] += 1
            m[s]["all_ok"] += c["label"] == "ok"
            if cat in ("C1", "C3") and c["factor"]:
                m[s]["f_n"] += 1
                m[s]["f_strict"] += c["passed"]
                m[s]["f_lenient"] += lenient(u, c)
        if cat == "C6":
            for c in u["calls"]:
                tok[s][n_sessions(u)].append(c["input_tokens"] + c["cache_creation_tokens"] + c["cache_read_tokens"])
        sc = load(ROOT / "data/eval" / f"{u['scenario']}.json")
        planner, first_worker = {}, {}
        for t in trace(d, u):
            if t["op"] != "agent_action":
                continue
            if t["role"] == "planner":
                planner[t["session"]] = t.get("tool")
            if t["role"] == "worker":
                first_worker.setdefault(t["session"], t)
            if t["role"] == "reviewer":
                m[s]["reviews"] += 1
                m[s]["rejected"] += str(t.get("answer", "")).lower().startswith("reject")
        for k, t in first_worker.items():
            if planner.get(k) == "update_record":
                m[s]["planner_update"] += 1
                m[s]["worker_update"] += t.get("tool") == "update_record"
            src = session_source(sc, k)
            if src is not None:
                m[s]["offered"] += 1
                m[s]["read"] += (t.get("tool") == src.tool and
                                 json.dumps(t.get("args"), sort_keys=True) == json.dumps(src.args, sort_keys=True))
    return m, cat_ok, cat_n, tok


def mean_tok(tok, s):
    return {n: round(sum(v) / len(v)) for n, v in sorted(tok[s].items())}


def render(a, b, name_a, name_b):
    ma, oka, na, ta = a
    mb, okb, nb, tb = b
    L = []

    def table(title, header, rows):
        L.append(f"## {title}\n")
        L.append("| " + " | ".join(header) + " |")
        L.append("|" + "---|" * len(header))
        L.extend("| " + " | ".join(str(x) for x in r) + " |" for r in rows)
        L.append("")

    rows = []
    for cat in CATS:
        for s in SYSTEMS:
            x, y = oka[(cat, s)]["ok"], okb[(cat, s)]["ok"]
            rows.append([cat, s, f"{x}/{na[(cat, s)]['n']}", f"{y}/{nb[(cat, s)]['n']}", y - x])
    table("1. Outcomes per category (checkpoints of the report table)", ["category", "system", name_a, name_b, "difference"], rows)

    table("2. All checkpoints of the repeat", ["system", name_a, name_b, "difference"],
          [[s, f"{ma[s]['all_ok']}/{ma[s]['all_n']}", f"{mb[s]['all_ok']}/{mb[s]['all_n']}", mb[s]["all_ok"] - ma[s]["all_ok"]] for s in SYSTEMS])

    table("3. C1/C3 factor checkpoints: strict and lenient rule", ["system", f"strict {name_a}", f"strict {name_b}",
          f"lenient {name_a}", f"lenient {name_b}"],
          [[s, f"{ma[s]['f_strict']}/{ma[s]['f_n']}", f"{mb[s]['f_strict']}/{mb[s]['f_n']}",
            f"{ma[s]['f_lenient']}/{ma[s]['f_n']}", f"{mb[s]['f_lenient']}/{mb[s]['f_n']}"] for s in SYSTEMS])

    table("4. Input tokens per call on C6 by history length (all calls)", ["system", name_a, name_b],
          [[s, mean_tok(ta, s), mean_tok(tb, s)] for s in SYSTEMS])

    table("5. Cost per unit, USD", ["system", name_a, name_b, "difference"],
          [[s, round(ma[s]["cost"] / max(ma[s]["units"], 1), 4), round(mb[s]["cost"] / max(mb[s]["units"], 1), 4),
            round(mb[s]["cost"] / max(mb[s]["units"], 1) - ma[s]["cost"] / max(ma[s]["units"], 1), 4)] for s in SYSTEMS])

    table("6. Agent behaviour", ["system", f"Worker read the offered source {name_a}", name_b,
          f"Reviewer rejected {name_a}", name_b,
          f"Planner update_record {name_a}", name_b, f"Worker first update_record after it {name_a}", name_b],
          [[s, f"{ma[s]['read']}/{ma[s]['offered']}", f"{mb[s]['read']}/{mb[s]['offered']}",
            f"{ma[s]['rejected']}/{ma[s]['reviews']}", f"{mb[s]['rejected']}/{mb[s]['reviews']}",
            ma[s]["planner_update"], mb[s]["planner_update"], ma[s]["worker_update"], mb[s]["worker_update"]] for s in SYSTEMS])
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--main", default=str(ROOT / "results/live/main"))
    ap.add_argument("--control", default=str(ROOT / "results/live/control"))
    ap.add_argument("--out", default=str(ROOT / "results/post_hoc/control_repeat.md"))
    a = ap.parse_args()
    text = ("# Control repeat against the committed run (repeat 0 on both sides; post hoc)\n\n"
            "One repeat gives no intervals. Differences below are run-to-run variation plus any real change; "
            "this is a side-by-side comparison, not a statistical test.\n\n"
            + render(metrics(a.main), metrics(a.control), "main r0", "control"))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
