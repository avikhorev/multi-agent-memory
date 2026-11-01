"""Paraphrase check (post hoc, decision D37, step 2).

Haiku rewrites the free text of the user messages and notes of 12 scenarios (3 each of C1, C2, C3, C6) in other
words. Values, dates, module names and the strings that the checks look for are kept literally; the template
phrases of the generator must disappear. Tool data and documents are left as they are. The paraphrased
scenarios are saved under results/post_hoc/paraphrase/scenarios and frozen by a commit before any system runs.

  python scripts/post_hoc_paraphrase.py paraphrase [--max-cost-usd 0.6]     # paid: the rewriting
  python scripts/post_hoc_paraphrase.py run [--max-cost-usd 1.4]            # paid: ours, ours3, BM25
  python scripts/post_hoc_paraphrase.py compare                             # no model
"""
import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

DATA = ROOT / "data/eval"
OUT = ROOT / "results/post_hoc/paraphrase"
SCEN = OUT / "scenarios"
SCENARIOS = [f"{c}-eval-000{n}" for c in ("C1", "C2", "C3") for n in (3, 4, 5)] + [f"C6-eval-000{n}" for n in (3, 4, 5)]
SYSTEMS = ["ours", "ours3", "shared_rag_bm25"]
TEMPLATE = ["hard rule", "standing instruction", "whatever anyone asks", "from now on", "per the vendor document",
            "per the status feed", "per the user", "status update", "reviewer note", "planner note", "worker note",
            "nobody objected", "will be repeated", "stands at", "noted ", "never ", "must not", "do not", "don't"]
SYSTEM_PROMPT = ("You rewrite short project messages in different words. For each item keep every string of KEEP exactly as "
                 "written (identical characters). Do not use any phrase of AVOID, even inside other words. Keep the meaning, "
                 "including who says what and any instruction or prohibition. Do not add facts. Reply with one strict JSON "
                 "object that maps each id to its rewritten text and nothing else.")


def spec_strings(scenario: dict) -> set[str]:
    out = {str(f["value"]) for f in scenario["facts"]}
    for cp in scenario["checkpoints"]:
        c, a = cp["context"], cp["answer"]
        out |= set(c["present"]) | set(c["absent"]) | {x for pair in c["disputed_both"] for x in pair}
        out |= ({a["expect"]} if a.get("expect") else set()) | set(a.get("stale", []))
        for pat in cp["action"]["forbidden"] + cp["action"]["required"]:
            out |= {str(v) for v in pat["args"].values()}
    return {s for s in out if s}


GENERIC = re.compile(r"\d{4}-\d{2}-\d{2}|\$?\d[\d,]*\d|\b[a-z]+ module\b|\bAtlas(?:/\w+)?\b|\b\w+\.\w+_\w+\b")


def keep_list(text: str, spec: set[str]) -> list[str]:
    return sorted({s for s in spec if s in text} | set(GENERIC.findall(text)), key=len, reverse=True)


def violations(old: str, new: str, keep: list[str]) -> list[str]:
    bad = [f"missing: {k}" for k in keep if k not in new]
    low_old, low_new = old.lower(), new.lower()
    if any(t in low_old for t in TEMPLATE):
        bad += [f"template phrase kept: {t.strip()}" for t in TEMPLATE if t in low_new]
    if new.strip() == old.strip():
        bad.append("unchanged")
    if len(new) > 3 * len(old) + 40:
        bad.append("too long")
    return bad


COST: list[float] = []  # cost of every rewriting call (recorded since decision D40)


def configure_v2():
    """The set of decision D40: C2-eval-0006..0011 and C5-eval-0006..0008, results in results/post_hoc/paraphrase2."""
    global SCENARIOS, OUT, SCEN
    SCENARIOS = [f"C2-eval-{n:04d}" for n in range(6, 12)] + [f"C5-eval-{n:04d}" for n in (6, 7, 8)]
    OUT = ROOT / "results/post_hoc/paraphrase2"
    SCEN = OUT / "scenarios"


def ask(llm, items: list[dict]) -> dict:
    prompt = "Items:\n" + json.dumps(items, ensure_ascii=False)
    out = llm.complete(SYSTEM_PROMPT, [{"role": "user", "content": prompt}], {})
    COST.append(float(getattr(out.usage, "cost_usd", 0) or 0))
    if out.refusal:
        return {}
    m = re.search(r"\{.*\}", out.text, re.S)
    try:
        data = json.loads(m.group(0)) if m else {}
    except ValueError:
        data = {}
    return {k: v for k, v in data.items() if isinstance(v, str)}


def paraphrase_scenario(llm, scenario: dict):
    """Returns (new scenario dict, None) or (None, reason). One retry for the events that failed."""
    spec = spec_strings(scenario)
    avoid = [t.strip() for t in TEMPLATE]
    new = json.loads(json.dumps(scenario))
    todo = []
    for sess in new["sessions"]:
        for e in sess["events"]:
            if e["type"] in ("user_message", "note"):
                todo.append((sess["index"], e, keep_list(e["text"], spec)))
    changed: dict[str, str] = {}
    pending = todo
    for attempt in (0, 1):
        by_session: dict[int, list] = {}
        for k, e, keep in pending:
            by_session.setdefault(k, []).append({"id": e["id"], "text": e["text"], "KEEP": keep, "AVOID": avoid})
        answers: dict[str, str] = {}
        for items in by_session.values():
            answers.update(ask(llm, items))
        failed = []
        for k, e, keep in pending:
            text = answers.get(e["id"], "")
            if text and not violations(e["text"], text, keep):
                changed[e["id"]] = text
            else:
                failed.append((k, e, keep))
        pending = failed
        if not pending:
            break
    if pending:
        why = "; ".join(f"{e['id']}: {violations(e['text'], changed.get(e['id'], '') or '(no answer)', keep)[:2]}" for _, e, keep in pending[:5])
        return None, f"{len(pending)} of {len(todo)} events failed after one retry ({why})"
    for sess in new["sessions"]:
        for e in sess["events"]:
            if e["id"] in changed:
                e["text"] = changed[e["id"]]
    for c in new["constraints"]:
        if c["event_id"] in changed:
            c["text"] = changed[c["event_id"]]
    return new, None


def paraphrase_all(max_cost):
    from mam.llm import ClaudeCliClient
    llm = ClaudeCliClient()
    SCEN.mkdir(parents=True, exist_ok=True)
    excluded = []

    def one(sid):
        return sid, paraphrase_scenario(llm, json.loads((DATA / f"{sid}.json").read_text()))

    with ThreadPoolExecutor(4) as pool:
        for sid, (sc, why) in pool.map(one, SCENARIOS):
            if sc is None:
                excluded.append((sid, why))
            else:
                (SCEN / f"{sid}.json").write_text(json.dumps(sc, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "excluded.md").write_text("# Excluded scenarios\n\n" + ("\n".join(f"- {s}: {w}" for s, w in excluded) or "none") + "\n")
    (OUT / "cost.json").write_text(json.dumps({"rewriting_calls": len(COST), "cost_usd": round(sum(COST), 6)}) + "\n")
    print("paraphrased", len(SCENARIOS) - len(excluded), "excluded", excluded, "cost", round(sum(COST), 4))


def included():
    return [p.stem for p in sorted(SCEN.glob("*.json"))]


def run(max_cost, max_minutes=25, workers=8):
    import mam.live as live
    import post_hoc_ours2 as p2
    from mam.llm import ClaudeCliClient
    from mam.run import plan_units, run_units
    llm = ClaudeCliClient()
    original = live.create
    live.create = lambda name, **kw: p2.Ours3(kw.get("limit", 2000), extractor="llm", llm=llm) if name == "ours3" else original(name, **kw)
    r = run_units(plan_units(SYSTEMS, included(), 1), llm, SCEN, OUT, workers=workers, max_minutes=max_minutes, max_cost_usd=max_cost)
    print(f"done {r.done}, skipped {r.skipped}, failed {r.failed}, cost ${r.cost_usd:.3f}, stopped_by {r.stopped_by}")
    sys.exit(r.exit_code)


def constraint_update(checkpoint: dict) -> bool:
    """A constraint checkpoint where the worker called update_record: the forbidden kind of action, whatever the field name.

    The scorer of the benchmark compares the exact field name of the forbidden pattern, so an edit of the same
    field under another name passes it; this count does not rely on the name (decision D39).
    """
    return checkpoint["kind"] == "constraint" and any(a.get("tool") == "update_record" for a in checkpoint.get("actions", []))


def corrected_ok(unit: dict) -> int:
    return sum(c["label"] == "ok" and not constraint_update(c) for c in unit["checkpoints"])


def rule_firing():
    """Whether the rule that pins constraints (rule_constraints) fires on the constraint messages, original and paraphrased."""
    from mam.extract import rule_constraints
    from mam.scenario import load
    from mam.simulate import entries
    rows = []
    for sid in included():
        if sid[:2] != "C2":
            continue
        res = []
        for base in (DATA, SCEN):
            sc = load(base / f"{sid}.json")
            ids = {c.event_id for c in sc.constraints}
            res.append([bool(rule_constraints(e)) for e in entries(sc) if e.id in ids])
        rows.append((sid, res[0], res[1]))
    return rows


def compare():
    fresh = ROOT / "results/post_hoc/fresh/units"
    groups = {"C2 (3 constraint checks + 9 value checks)": ("C2",), "C1/C3": ("C1", "C3"), "C6": ("C6",), "all": ("C1", "C2", "C3", "C6")}
    rows = ["# Paraphrase check: checks passed on the original and on the paraphrased scenarios (same systems, same scenarios)", "",
            "| system | group | original | paraphrased | loss |", "|---|---|---|---|---|"]
    corr = ["", "## Corrected count: a constraint check with an update_record action counts as failed (decision D39)", "",
            "| system | original, corrected | paraphrased, corrected | loss | constraint checks with update_record: original | paraphrased |", "|---|---|---|---|---|---|"]
    verdict, verdict_c = [], []
    for s in SYSTEMS:
        for g, cats in groups.items():
            o = p = n = 0
            for sid in included():
                if sid[:2] not in cats:
                    continue
                a = json.loads((fresh / f"{s}__{sid}__r0.json").read_text())
                b = json.loads((OUT / "units" / f"{s}__{sid}__r0.json").read_text())
                o += sum(c["label"] == "ok" for c in a["checkpoints"])
                p += sum(c["label"] == "ok" for c in b["checkpoints"])
                n += len(b["checkpoints"])
            loss = (o - p) / o if o else 0.0
            rows.append(f"| {s} | {g} | {o}/{n} | {p}/{n} | {loss:.0%} |")
            if g == "all" and s == "ours3":
                verdict.append("robust" if loss <= 0.10 else "fragile" if loss > 0.25 else "partial")
        co = cp = uo = up = n = 0
        for sid in included():
            a = json.loads((fresh / f"{s}__{sid}__r0.json").read_text())
            b = json.loads((OUT / "units" / f"{s}__{sid}__r0.json").read_text())
            co, cp = co + corrected_ok(a), cp + corrected_ok(b)
            uo += sum(constraint_update(c) for c in a["checkpoints"])
            up += sum(constraint_update(c) for c in b["checkpoints"])
            n += len(b["checkpoints"])
        loss = (co - cp) / co if co else 0.0
        corr.append(f"| {s} | {co}/{n} | {cp}/{n} | {loss:.0%} | {uo} | {up} |")
        if s == "ours3":
            verdict_c.append("robust" if loss <= 0.10 else "fragile" if loss > 0.25 else "partial")
        if s == "ours":
            ours_c = "robust" if loss <= 0.10 else "fragile" if loss > 0.25 else "partial"
    fire = ["", "## Does the rule that pins constraints fire on the constraint messages?", "",
            "| scenario | original | paraphrased |", "|---|---|---|"]
    fire += [f"| {sid} | {o} | {p} |" for sid, o, p in rule_firing()]
    rows += corr + fire
    rows += ["", f"Verdict for ours3 (loss on the sum of the four groups, thresholds 10% and 25%): {verdict[0] if verdict else 'n/a'}; "
             f"corrected count: ours3 {verdict_c[0] if verdict_c else 'n/a'}, ours {ours_c}."]
    (OUT / "comparison.md").write_text("\n".join(rows) + "\n")
    print("\n".join(rows))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["paraphrase", "run", "compare"])
    ap.add_argument("--max-cost-usd", type=float, default=1.4)
    a = ap.parse_args()
    {"paraphrase": lambda: paraphrase_all(a.max_cost_usd), "run": lambda: run(a.max_cost_usd), "compare": compare}[a.cmd]()
