"""ours2: a small post hoc iteration of the structured memory (decision D30).

Three changes on top of `ours`, without touching src/mam:
1. a buffer of the records of the open session (not yet through end_session);
2. the rest of the limit is filled with BM25 over old raw records, minus records that carry a losing version;
3. an untrusted value newer than the trusted one is shown as a dispute instead of being dropped.
Order under the limit: constraints, buffer, facts, fragments, filler.
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from mam.extract import UNKNOWN_TIME
from mam.guard import split_untrusted
from mam.systems.ours import Ours
from mam.systems.ranking import bm25_scores
from mam.tokens import count
from mam.types import ContextItem
from mam.systems.base import make_context

ALL_CHANGES = frozenset({"buffer", "filler", "disputes"})


class Ours2(Ours):
    def __init__(self, limit, ablate2=frozenset(), **kw):
        super().__init__(limit, **kw)
        self.off = frozenset(ablate2)

    def _resolve(self, versions):
        n = len(self.last_trace)
        cur = super()._resolve(versions)
        if "disputes" in self.off or not cur:
            return cur
        dropped = {t["entry_id"] for t in self.last_trace[n:] if t.get("reason", "").startswith("untrusted source")}
        newer = [v for v in versions if v.entry.id in dropped and (v.time == UNKNOWN_TIME or v.time > cur[0].time)]
        return cur + newer if cur[0].trust > 0 else cur

    def _buffer(self, reader):
        """Raw records of the open session, oldest first; untrusted ones only through the guard, as quoted data."""
        out = []
        for e in sorted(self._entries.values(), key=lambda e: e.clock):
            if e.id in self._done or not self._can_see(e, reader):
                continue
            if e.trust == "untrusted" and "trust" not in self.ablate:
                out += [ContextItem(f"buf-{e.id}-{n}", "quoted_data", t, (e.id,)) for n, t in enumerate(split_untrusted(e.text)[0])]
            else:
                out.append(ContextItem(f"buf-{e.id}", "raw", e.text, (e.id,)))
        return out

    def _filler(self, reader):
        """Old raw records that carry no losing version, best BM25 match first."""
        losing = set()
        for versions in self._versions.values():
            seen = [v for v in versions if self._can_see(v.entry, reader)]
            if seen:
                keep = {c.fact.value for c in self._resolve(seen)}
                losing |= {v.entry.id for v in seen if v.fact.value not in keep}
        docs = [e for e in self._entries.values() if e.id in self._done and e.trust != "untrusted"
                and e.id not in losing and self._can_see(e, reader)]
        ranked = sorted(zip(bm25_scores(reader.query, [e.text for e in docs]), docs), key=lambda p: (-p[0], -p[1].clock))
        return [ContextItem(f"fill-{e.id}", "raw", e.text, (e.id,)) for _, e in ranked]

    def context(self, reader):
        limit = self.limit
        base = super().context(reader).items
        cons = [i for i in base if i.kind == "constraint"]
        used = sum(count(i.text) for i in cons)
        buf = []
        for item in reversed(self._buffer(reader) if "buffer" not in self.off else []):  # newest first
            if used + count(item.text) <= limit:
                buf.insert(0, item)
                used += count(item.text)
        self.limit = limit - (used - sum(count(i.text) for i in cons))
        try:
            rest = [i for i in super().context(reader).items if i.kind != "constraint"]
        finally:
            self.limit = limit
        used += sum(count(i.text) for i in rest)
        fill = []
        for item in self._filler(reader) if "filler" not in self.off else []:
            if used + count(item.text) <= limit:
                fill.append(item)
                used += count(item.text)
        return make_context(cons + buf + rest + fill)


# ---- memory-level run and comparison (no model) ---------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ["ours2@cache"] + [f"ours2@cache-no_{c}" for c in ("buffer", "filler", "disputes")]
OUT = ROOT / "results/post_hoc/ours2"


def make_system(cfg, limit=2000, cache_path=None):
    """memory_eval.make_system for the ours2 names: ours2@cache or ours2@cache-no_<change>."""
    _, _, rest = cfg.partition("@")
    extractor, _, off = rest.partition("-")
    return Ours2(limit, ablate2={off[3:]} if off else frozenset(), extractor=extractor, cache_path=cache_path)


def memory_level():
    from mam import memory_eval
    original = memory_eval.make_system
    memory_eval.make_system = lambda cfg, limit=2000, cache_path=None: (
        make_system(cfg, limit, cache_path) if cfg.startswith("ours2") else original(cfg, limit, cache_path))
    for split in ("eval", "holdout"):
        sys.argv = ["memory_eval", "--split", split, "--out", str(OUT / split), "--systems", ",".join(VARIANTS),
                    "--cache", str(ROOT / f"results/extraction/{split}/cache.jsonl")]
        memory_eval.main()


def compare():
    from mam.tables import METRICS
    lines = ["# ours2 against ours@cache at the memory level (no model; post hoc)", ""]
    for split in ("eval", "holdout"):
        res = {}
        for name, path in [("ours@cache", ROOT / f"results/memory_level/{split}/ours@cache.jsonl")] + \
                          [(v, OUT / split / f"{v}.jsonl") for v in VARIANTS]:
            res[name] = [r for r in map(json.loads, path.read_text().splitlines()) if r["record"] == "checkpoint"]
        lines += [f"## {split}", "", "| metric | " + " | ".join(res) + " |", "|---|" + "---|" * len(res)]
        lines.append("| checkpoints passed | " + " | ".join(f"{sum(r['passed'] for r in rs)}/{len(rs)}" for rs in res.values()) + " |")
        for cat, label, fn, _ in METRICS:
            cells = []
            for rs in res.values():
                sel = [fn(r) for r in rs if r["category"] == cat]
                cells.append(f"{sum(map(float, sel)) / len(sel):.2f}" if sel else "-")
            lines.append(f"| {cat} {label} | " + " | ".join(cells) + " |")
        lines.append("")
    (OUT / "memory_level.md").write_text("\n".join(lines))
    print("\n".join(lines))


# ---- live stage (stage B of D30, paid) and the criteria -------------------------------------------------

LIVE_OUT = OUT / "live"


def live_units():
    from mam.run import plan_units
    from mam.selection import select_live
    return plan_units(["ours2"], select_live(ROOT / "data/eval/manifest.json", "A"), 2)


def run_live_stage(max_cost, max_minutes, workers=8):
    import mam.live as live
    from mam.llm import ClaudeCliClient
    from mam.run import run_units
    llm = ClaudeCliClient()
    original = live.create
    live.create = lambda name, **kw: Ours2(kw.get("limit", 2000), extractor="llm", llm=llm) if name == "ours2" else original(name, **kw)
    r = run_units(live_units(), llm, ROOT / "data/eval", LIVE_OUT, workers=workers, max_minutes=max_minutes, max_cost_usd=max_cost)
    print(f"done {r.done}, skipped {r.skipped}, failed {r.failed}, cost ${r.cost_usd:.3f}, stopped_by {r.stopped_by}")
    sys.exit(r.exit_code)


def criteria():
    sys.path.insert(0, str(ROOT / "scripts"))
    import post_hoc_control_repeat as cr
    from mam.live_tables import category
    rows = {}
    for label, d in (("ours (main, 2 repeats)", ROOT / "results/live/main"), ("ours2 (2 repeats)", LIVE_OUT)):
        us = [json.loads(f.read_text()) for f in sorted((d / "units").glob("*.json"))]
        us = [u for u in us if u["system"] in ("ours", "ours2")]
        rej = n_rev = ok = n = fs = fn = read = offered = 0
        for u in us:
            sc = u["scenario"]
            for c in u["checkpoints"]:
                n += 1
                ok += c["label"] == "ok"
                if category(u) in ("C1", "C3") and c["factor"]:
                    fn += 1
                    fs += c["passed"]
            tf = d / "traces" / f"{u['system']}__{sc}__r{u['repeat']}.jsonl"
            first = {}
            scn = cr.load(ROOT / "data/eval" / f"{sc}.json")
            for line in tf.read_text().splitlines():
                t = json.loads(line)
                if t["op"] == "agent_action" and t["role"] == "reviewer":
                    n_rev += 1
                    rej += str(t.get("answer", "")).lower().startswith("reject")
                if t["op"] == "agent_action" and t["role"] == "worker":
                    first.setdefault(t["session"], t)
            for k, t in first.items():
                src = cr.session_source(scn, k)
                if src is not None:
                    offered += 1
                    read += t.get("tool") == src.tool and json.dumps(t.get("args"), sort_keys=True) == json.dumps(src.args, sort_keys=True)
        rows[label] = (rej, n_rev, ok, n, fs, fn, read, offered, sum(u["cost_usd"] for u in us) / len(us), len(us))
    out = ["# ours2 live stage against ours (criteria of D30)", "",
           "| system | Reviewer rejected | all checks ok | strict factor C1/C3 | Worker read the offered source | cost per unit, USD | units |", "|---|---|---|---|---|---|---|"]
    for k, v in rows.items():
        out.append(f"| {k} | {v[0]}/{v[1]} | {v[2]}/{v[3]} | {v[4]}/{v[5]} | {v[6]}/{v[7]} | {v[8]:.4f} | {v[9]} |")
    r2 = rows["ours2 (2 repeats)"]
    confirm = r2[0] <= 204 and r2[2] >= 134 and r2[4] >= 11
    refute = r2[0] > 270 or r2[2] <= 124 or r2[4] <= 9
    out += ["", f"Criteria: confirmation (all three) rejected <= 204, all checks >= 134, strict factor >= 11: {'met' if confirm else 'not met'}; "
            f"refutation (any) rejected > 270, all checks <= 124, strict factor <= 9: {'met' if refute else 'not met'}; "
            f"verdict: {'confirmed' if confirm else 'refuted' if refute else 'partial'}."]
    (OUT / "criteria.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["memory", "compare", "live", "criteria"])
    ap.add_argument("--max-cost-usd", type=float, default=1.5)
    ap.add_argument("--max-minutes", type=float, default=25)
    a = ap.parse_args()
    if a.cmd == "live":
        run_live_stage(a.max_cost_usd, a.max_minutes)
    {"memory": memory_level, "compare": compare, "criteria": criteria}.get(a.cmd, lambda: None)()
