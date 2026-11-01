"""External baselines on the benchmark (decision D42). python external/run.py <system> pilot|run|tables [--max-cost-usd X]
The system is replaced by patching mam.live.create; nothing in the project imports this folder."""
import argparse
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "external"), str(ROOT / "scripts")]
import mam.live as live  # noqa: E402
from mam.llm import ClaudeCliClient  # noqa: E402
from mam.run import plan_units, run_units  # noqa: E402

OUT = ROOT / "results/post_hoc/external"
R = ROOT / "results/post_hoc"
A_IDS = [f"C2-eval-{n:04d}" for n in range(6, 12)] + [f"C5-eval-{n:04d}" for n in (6, 7, 8)]
RIVALS = {"fresh": {"ours": R / "fresh", "ours3": R / "fresh", "shared_rag_bm25": R / "fresh", "full_history_meta": R / "fresh", "ours4": R / "ours4/setB"},
          "paraphrase2": {"ours": R / "ours4/setA", "ours3": R / "ours4/setA", "ours4": R / "ours4/setA"}}


def sets():
    from post_hoc_fresh import fresh_ids
    return {"fresh": (ROOT / "data/eval", fresh_ids()), "paraphrase2": (R / "paraphrase2/scenarios", A_IDS)}


def stats(base, system, ids=None):
    s = dict(n=0, ok=0, fn=0, fs=0, cn=0, cs=0, cd=0, inj=0, injn=0, rej=0, rev=0, cost=0.0, sec=0.0, units=0)
    for f in sorted((base / "units").glob(f"{system}__*.json")):
        u = json.loads(f.read_text())
        if ids and u["scenario"] not in ids:
            continue
        s["units"] += 1; s["cost"] += u["cost_usd"]; s["sec"] += u["totals"]["llm_latency_s"]  # noqa: E702
        for c in u["checkpoints"]:
            s["n"] += 1; s["ok"] += c["label"] == "ok"  # noqa: E702
            if c["factor"] and u["scenario"][:2] in ("C1", "C3"):
                s["fn"] += 1; s["fs"] += c["passed"]  # noqa: E702
            if c["kind"] == "constraint":
                s["cn"] += 1; s["cs"] += c["label"] == "ok"; s["cd"] += c["label"] == "ok" and not any(a.get("tool") == "update_record" for a in c["actions"])  # noqa: E702
            if c["kind"] == "injection":
                s["injn"] += 1; s["inj"] += c["label"] == "ok"  # noqa: E702
        for line in (base / "traces" / f"{f.stem}.jsonl").read_text().splitlines():
            t = json.loads(line)
            if t["op"] == "agent_action" and t["role"] == "reviewer":
                s["rev"] += 1; s["rej"] += str(t.get("answer", "")).lower().startswith("reject")  # noqa: E702
    return s


def tables(system):
    rows = ["| set | system | units | all checks | strict C1/C3 | Reviewer rejected | constraint (strict / D39) | injection | USD per unit | model s per unit |", "|---|---|---|---|---|---|---|---|---|---|"]
    for name, rivals in RIVALS.items():
        own = OUT / system / name
        ids = {p.stem.split("__")[1] for p in (own / "units").glob("*.json")} if (own / "units").exists() else set()  # rivals on the same scenarios
        for sysname, base in [(system, own)] + list(rivals.items()):
            if ids and (base / "units").exists() and (s := stats(base, sysname, None if base == own else ids))["units"]:
                rows.append(f"| {name} | {sysname} | {s['units']} | {s['ok']}/{s['n']} | {s['fs']}/{s['fn']} | {s['rej']}/{s['rev']} | {s['cs']} / {s['cd']} of {s['cn']} | {s['inj']}/{s['injn']} | {s['cost'] / s['units']:.4f} | {s['sec'] / s['units']:.0f} |")
    (OUT / system).mkdir(parents=True, exist_ok=True)
    (OUT / system / "tables.md").write_text("\n".join(rows) + "\n")
    print("\n".join(rows))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("system"); ap.add_argument("cmd", choices=["pilot", "run", "tables"]); ap.add_argument("--max-cost-usd", type=float, default=1.0); ap.add_argument("--fresh-cats", default=""); ap.add_argument("--only", default="")  # noqa: E702
    a = ap.parse_args()
    if a.cmd == "tables":
        tables(a.system); sys.exit()  # noqa: E702
    mod, llm, orig = importlib.import_module(f"{a.system}_adapter"), ClaudeCliClient(), live.create
    live.create = lambda name, **kw: mod.create(kw.get("limit", 2000), llm) if name == a.system else orig(name, **kw)
    todo = {"pilot": {"pilot": (ROOT / "data/eval", ["C2-eval-0003"])}, "run": sets()}[a.cmd]
    for name, (data, ids) in [(n, v) for n, v in todo.items() if not a.only or n == a.only]:
        ids = [i for i in ids if not a.fresh_cats or i[:2] in a.fresh_cats.split(",")]  # D43: shortened sets
        r = run_units(plan_units([a.system], ids, 1), llm, data, OUT / a.system / name, workers=8, max_minutes=25, max_cost_usd=a.max_cost_usd)
        print(name, f"done {r.done}, skipped {r.skipped}, failed {r.failed}, cost ${r.cost_usd:.3f}, stopped_by {r.stopped_by}")
