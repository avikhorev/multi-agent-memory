"""Additional analysis after the freeze (not pre-registered): controls for the headline comparisons.

Reads saved results only; no model is called, nothing in src/mam, data or raw results is changed.
Writes results/post_hoc/controls.md.

  python scripts/post_hoc_controls.py

Sections: (1) agent behaviour per system, (2) decomposition of the memory-level failures,
(3) write-side cost and time, (4) live outcome totals, (5) context growth on C6 without the
extractor calls, (6) implicit-update extraction split by whether the value is written in the message.
"""
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mam.live import session_source  # noqa: E402
from mam.live_tables import category, selected, n_sessions  # noqa: E402
from mam.scenario import load  # noqa: E402
from mam.scoring import normalize  # noqa: E402
from mam.simulate import entries  # noqa: E402

LIVE = ROOT / "results/live/main"
SYSTEMS = ["full_history", "ours", "rolling_summary", "shared_rag_bm25", "sliding_window"]
OUT = ROOT / "results/post_hoc/controls.md"
lines: list[str] = []


def table(header, rows):
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "---|" * len(header))
    for r in rows:
        lines.append("| " + " | ".join(str(x) for x in r) + " |")
    lines.append("")


def units():
    return [json.loads(f.read_text()) for f in sorted((LIVE / "units").glob("*.json"))]


def trace(u):
    m = u["manifest"]
    f = LIVE / "traces" / f"{m['system']}__{m['scenario']}__r{m['repeat']}.jsonl"
    return [json.loads(x) for x in f.read_text().splitlines() if x.strip()]


def agent_behaviour(us):
    lines.append("## 1. Agent behaviour per system (same prompts for all systems)\n")
    stats = {s: collections.Counter() for s in SYSTEMS}
    for u in us:
        m = u["manifest"]
        sc = load(ROOT / "data/eval" / f"{m['scenario']}.json")
        c6 = m["scenario"].startswith("C6")
        st = stats[m["system"]]
        first_worker, planner_tool, worker_any_update = {}, {}, set()
        for t in trace(u):
            if t["op"] != "agent_action":
                continue
            if t["role"] == "planner":
                planner_tool[t["session"]] = t.get("tool")
            if t["role"] == "worker":
                first_worker.setdefault(t["session"], t)
                if t.get("tool") == "update_record":
                    worker_any_update.add(t["session"])
            if t["role"] == "reviewer":
                st["reviews"] += 1
                rej = str(t.get("answer", "")).lower().startswith("reject")
                st["rejected"] += rej
                if t["session"] >= 5:
                    st["reviews5"] += 1
                    st["rejected5"] += rej
        for k, t in first_worker.items():
            if planner_tool.get(k) == "update_record":
                st["planner_update"] += 1
                st["worker_update_after_planner_update"] += t.get("tool") == "update_record"
                st["worker_any_update"] += k in worker_any_update
            src = session_source(sc, k)
            if src is None:
                continue
            read = t.get("tool") in ("read_document", "read_status") and \
                t.get("tool") == src.tool and json.dumps(t.get("args"), sort_keys=True) == json.dumps(src.args, sort_keys=True)
            st["offered"] += 1
            st["read"] += read
            st["update_first"] += t.get("tool") == "update_record"
            if c6:
                st["offered_c6"] += 1
                st["read_c6"] += read
    lines.append("Planner chose update_record, and what the Worker did first in those sessions:\n")
    table(["system", "Planner chose update_record (sessions)", "Worker's first action was update_record", "Worker called update_record in either call"],
          [[s, stats[s]["planner_update"], stats[s]["worker_update_after_planner_update"], stats[s]["worker_any_update"]] for s in SYSTEMS])
    table(["system", "Worker read the offered source (sessions with a source)", "of them on C6",
           "first action update_record (offered source)", "Reviewer rejected", "rejected in sessions 5+"],
          [[s, f"{stats[s]['read']} of {stats[s]['offered']}", f"{stats[s]['read_c6']} of {stats[s]['offered_c6']}",
            stats[s]["update_first"], f"{stats[s]['rejected']} of {stats[s]['reviews']}",
            f"{stats[s]['rejected5']} of {stats[s]['reviews5']}"] for s in SYSTEMS])


def decomposition():
    lines.append("## 2. Memory-level failures on eval by kind of violation\n")
    names = {"full_history": "full_history", "sliding_window": "sliding_window", "shared_rag_bm25": "shared_rag_bm25",
             "rolling_summary@cache": "rolling_summary@cache", "ours@cache": "ours@cache"}
    rows = []
    for fname, label in names.items():
        c = collections.Counter()
        for line in (ROOT / "results/memory_level/eval" / f"{fname}.jsonl").read_text().splitlines():
            r = json.loads(line)
            if r.get("record") != "checkpoint" or r["passed"]:
                continue
            v = r["violations"]
            kinds = set()
            for x in v:
                kinds.add("disputed pair" if x.startswith("disputed") else
                          "present missing" if x.startswith("present missing") else
                          "absent found" if x.startswith("absent found") else
                          "outside quoted data" if x.startswith("found outside") else "other")
            key = (r["category"], " + ".join(sorted(kinds)))
            c[key] += 1
        for (cat, kinds), n in sorted(c.items()):
            rows.append([label, cat, kinds, n])
        rows.append([label, "all", "total failures", sum(c.values())])
    table(["system", "category", "violations of the failed check", "failed checks"], rows)


def cost(us):
    lines.append("## 3. Write-side cost and time per unit (model calls made by the memory itself)\n")
    rows = []
    for s in SYSTEMS:
        mine = [u for u in us if u["manifest"]["system"] == s]
        ext = [c for u in mine for c in u["calls"] if c["role"] in ("extractor", "summary")]
        agents = [c for u in mine for c in u["calls"] if c["role"] not in ("extractor", "summary")]
        n = len(mine)
        sess = sum(n_sessions(u) for u in mine)
        tok = lambda cs: sum(c["input_tokens"] + c["cache_creation_tokens"] + c["cache_read_tokens"] for c in cs)
        rows.append([s, round(len(ext) / n, 1), round(tok(ext) / n), round(sum(c["latency_s"] for c in ext) / n, 1),
                     round(sum(c["cost_usd"] for c in ext) / n, 4), round(sum(c["latency_s"] for c in ext) / sess, 2),
                     round(sum(c["latency_s"] for c in agents) / n, 1), round(sum(c["latency_s"] for c in mine and [x for u in mine for x in u["calls"]]) / n, 1)])
    table(["system", "memory calls per unit", "input tokens per unit", "memory model time per unit, s",
           "memory cost per unit, USD", "memory model time per session, s", "agent model time per unit, s",
           "all model time per unit, s"], rows)
    lines.append("C0 only (short histories), all calls:\n")
    c0 = {}
    for s in SYSTEMS:
        mine = [u for u in us if u["manifest"]["system"] == s and category(u) == "C0"]
        c0[s] = (sum(len(u["calls"]) for u in mine) / len(mine), sum(u["totals"]["llm_latency_s"] for u in mine) / len(mine),
                 sum(u["cost_usd"] for u in mine) / len(mine), sum(1 for u in mine for c in u["checkpoints"] if c["label"] == "ok"),
                 sum(len(u["checkpoints"]) for u in mine))
    table(["system", "calls per unit", "model time per unit, s", "cost per unit, USD", "ok", "checkpoints"],
          [[s, round(v[0], 1), round(v[1], 1), round(v[2], 4), v[3], v[4]] for s, v in c0.items()])
    o, f = c0["ours"], c0["full_history"]
    lines.append(f"C0: ours vs full_history, calls {o[0] / f[0] - 1:+.0%}, model time {o[1] / f[1] - 1:+.0%}.\n")


def totals(us):
    lines.append("## 4. Live outcome totals\n")
    allc, shown, rest = collections.Counter(), collections.Counter(), collections.Counter()
    nall, nshown, nrest = collections.Counter(), collections.Counter(), collections.Counter()
    for u in us:
        s, cat = u["manifest"]["system"], category(u)
        sel = {c["checkpoint"] for c in selected(u)}
        for c in u["checkpoints"]:
            ok = c["label"] == "ok"
            allc[s] += ok
            nall[s] += 1
            if c["checkpoint"] in sel:
                shown[s] += ok
                nshown[s] += 1
            if not (cat in ("C1", "C3") and c["factor"]):
                rest[s] += ok
                nrest[s] += 1
    table(["system", "all checkpoints ok", "of", "checkpoints in the headline table ok", "of",
           "all except the factor checkpoints of C1 and C3 ok", "of"],
          [[s, allc[s], nall[s], shown[s], nshown[s], rest[s], nrest[s]] for s in SYSTEMS])


def growth(us):
    lines.append("## 5. Input tokens per call on C6 by history length, agent calls only\n")
    rows = []
    for s in SYSTEMS:
        pts = collections.defaultdict(list)
        for u in us:
            if u["manifest"]["system"] == s and category(u) == "C6":
                for c in u["calls"]:
                    if c["role"] not in ("extractor", "summary"):
                        pts[n_sessions(u)].append(c["input_tokens"] + c["cache_creation_tokens"] + c["cache_read_tokens"])
        mean = [(n, sum(v) / len(v)) for n, v in sorted(pts.items())]
        mx, my = sum(x for x, _ in mean) / len(mean), sum(y for _, y in mean) / len(mean)
        sl = sum((x - mx) * (y - my) for x, y in mean) / sum((x - mx) ** 2 for x, _ in mean)
        rows.append([s] + [f"{n}: {round(v)}" for n, v in mean] + [round(sl, 1)])
    table(["system", "length 10", "length 20", "length 30", "slope, tokens per added session"], rows)
    n = collections.Counter(u["manifest"]["scenario"].split("-")[0] for u in us if u["manifest"]["system"] == "ours")
    lines.append("Units per category for one system (scenarios x repeats): " + ", ".join(f"{k} {v}" for k, v in sorted(n.items())) + ".\n")


def h2():
    lines.append("## 6. Implicit-update extraction: value written in the message or computed\n")
    rows = []
    for split, data, cache in (("eval", "data/eval", "results/extraction/eval/cache.jsonl"),
                               ("holdout", "holdout", "results/extraction/holdout/cache.jsonl")):
        got = {}
        for line in (ROOT / cache).read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("kind") != "summary":
                    got[(r["task_id"], r["entry_id"])] = r
        c = collections.Counter()
        for p in sorted((ROOT / data).glob("*.json")):
            if "sessions" not in json.loads(p.read_text()):
                continue  # manifest and other non-scenario files
            s = load(p)
            if s.variant != "implicit":
                continue
            for e in entries(s):
                if not e.id.startswith("x-"):
                    continue
                row = got.get((f"task-{s.id}", e.id))
                have = set() if row is None or row["refusal"] else {(f["entity"], f["attribute"], f["value"]) for f in row["facts"]}
                for f in e.oracle_facts:
                    kind = "written" if normalize(f.value) in normalize(e.text) else "computed"
                    c[kind + "_expected"] += 1
                    c[kind + "_found"] += (f.entity, f.attribute, f.value) in have
        rows.append([split, c["written_expected"], c["written_found"], c["computed_expected"], c["computed_found"]])
    table(["split", "implicit updates with the value written in the message", "found",
           "implicit updates with a computed value", "found"], rows)


if __name__ == "__main__":
    us = units()
    agent_behaviour(us)
    decomposition()
    cost(us)
    totals(us)
    growth(us)
    h2()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("# Controls (additional analysis after the freeze)\n\n" + "\n".join(lines))
    print("\n".join(lines))
