"""Check on scenarios new to the live layer (post hoc, decision D37).

Selection rule, applied to the eval manifest only (ids, categories, variants and lengths; no content, no results):
the scenarios that follow the variant-A choice in manifest order, with the same split: 3 per category C0-C5
(C1 and C3: two implicit and one explicit, like variant A), and for C6 one per length 10, 20 and 30.

  python scripts/post_hoc_fresh.py plan            # list the 21 scenarios and the 105 units, no model
  python scripts/post_hoc_fresh.py run [--max-cost-usd 4 --max-minutes 25]     # paid
  python scripts/post_hoc_fresh.py criteria        # the preset criteria on the saved units, no model
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from mam.selection import select_live  # noqa: E402

DATA = ROOT / "data/eval"
OUT = ROOT / "results/post_hoc/fresh"
SYSTEMS = ["ours", "ours3", "shared_rag_bm25", "full_history", "full_history_meta"]


def fresh_ids() -> list[str]:
    manifest = json.loads((DATA / "manifest.json").read_text())["scenarios"]
    used = set(select_live(DATA / "manifest.json", "A"))
    by_cat: dict[str, list[dict]] = {}
    for s in manifest:
        if s["id"] not in used:
            by_cat.setdefault(s["category"], []).append(s)
    picked: list[str] = []
    for cat in ("C0", "C1", "C2", "C3", "C4", "C5"):
        pool = by_cat[cat]
        if cat in ("C1", "C3"):
            picked += [s["id"] for s in [x for x in pool if x["variant"] == "implicit"][:2] + [x for x in pool if x["variant"] == "explicit"][:1]]
        else:
            picked += [s["id"] for s in pool[:3]]
    for length in (10, 20, 30):
        picked.append(next(s["id"] for s in by_cat["C6"] if s["n_sessions"] == length))
    return picked


def units():
    from mam.run import plan_units
    return plan_units(SYSTEMS, fresh_ids(), 1)


def run(max_cost, max_minutes, workers=8):
    import mam.live as live
    import post_hoc_ours2 as p2
    import post_hoc_presentation as pp
    from mam.llm import ClaudeCliClient
    from mam.run import run_units
    llm = ClaudeCliClient()
    meta = pp.make_create(llm)  # handles *_meta; other names go to the original create
    live.create = lambda name, **kw: (p2.Ours3(kw.get("limit", 2000), extractor="llm", llm=llm) if name == "ours3" else meta(name, **kw))
    r = run_units(units(), llm, DATA, OUT, workers=workers, max_minutes=max_minutes, max_cost_usd=max_cost)
    print(f"done {r.done}, skipped {r.skipped}, failed {r.failed}, cost ${r.cost_usd:.3f}, stopped_by {r.stopped_by}")
    sys.exit(r.exit_code)


def criteria():
    import post_hoc_control_repeat as cr
    from mam.live_tables import category
    us = [json.loads(f.read_text()) for f in sorted((OUT / "units").glob("*.json"))]
    stats = {s: dict(ok=0, n=0, fs=0, fn=0, rej=0, rev=0, cost=0.0, units=0) for s in SYSTEMS}
    for u in us:
        st = stats[u["system"]]
        st["units"] += 1
        st["cost"] += u["cost_usd"]
        for c in u["checkpoints"]:
            st["n"] += 1
            st["ok"] += c["label"] == "ok"
            if category(u) in ("C1", "C3") and c["factor"]:
                st["fn"] += 1
                st["fs"] += c["passed"]
        for t in cr.trace(OUT, u):
            if t["op"] == "agent_action" and t["role"] == "reviewer":
                st["rev"] += 1
                st["rej"] += str(t.get("answer", "")).lower().startswith("reject")
    lines = ["# Fresh scenarios: ours3 against the others (preset criteria of D37)", "",
             "| system | all checks ok | strict factor C1/C3 | Reviewer rejected | cost per unit, USD | units |", "|---|---|---|---|---|---|"]
    for s in SYSTEMS:
        v = stats[s]
        lines.append(f"| {s} | {v['ok']}/{v['n']} | {v['fs']}/{v['fn']} | {v['rej']}/{v['rev']} | {v['cost'] / max(v['units'], 1):.4f} | {v['units']} |")
    me = stats["ours3"]
    rivals = ["ours", "shared_rag_bm25", "full_history_meta"]
    lead = {r: me["ok"] - stats[r]["ok"] for r in rivals}
    confirm = all(d > 4 for d in lead.values()) and me["fs"] >= 5 and me["rej"] <= 96
    refute = any(d < -4 for d in lead.values()) or me["fs"] <= 3
    lines += ["", "Lead of ours3 in checks: " + ", ".join(f"{r} {d:+d}" for r, d in lead.items()),
              f"Verdict: {'confirmed' if confirm else 'refuted' if refute else 'neither (differences within the +-4 spread or a criterion not met)'}."]
    (OUT / "criteria.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["plan", "run", "criteria"])
    ap.add_argument("--max-cost-usd", type=float, default=4.0)
    ap.add_argument("--max-minutes", type=float, default=25)
    a = ap.parse_args()
    if a.cmd == "plan":
        ids = fresh_ids()
        print(len(ids), "scenarios,", len(units()), "units:", ", ".join(ids))
    elif a.cmd == "run":
        run(a.max_cost_usd, a.max_minutes)
    else:
        criteria()
