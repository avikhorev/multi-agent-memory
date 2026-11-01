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


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["memory", "compare"])
    cmd = ap.parse_args().cmd
    memory_level() if cmd == "memory" else compare()
