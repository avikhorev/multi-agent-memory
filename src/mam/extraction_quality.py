"""Quality of the saved extractions against the reference (hypothesis H2: implicit updates may be skipped).

  python -m mam.extraction_quality <cache.jsonl> <data-dir>
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

from mam.scenario import load
from mam.simulate import entries

def quality(cache_path, data_dir) -> dict:
    """Counts tp, fp and fn by (kind of update, part) over the triples (entity, attribute, value).

    tp — fact found and correct; fp — found extra or incorrect; fn — expected but missed.
    part = "update" for the facts of factor events (id starts with x-) and "base" for the others.
    If the extraction of a record was rejected (refusal), all its expected facts count as missed.
    """
    # Read the cache: by key (task, record) we store the extraction line; summaries are skipped.
    rows = {}
    for line in Path(cache_path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            if r.get("kind") != "summary":
                rows[(r["task_id"], r["entry_id"])] = r
    out: dict = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    refusals = 0
    # task_id has the form "task-<scenario id>"; cut off the prefix "task-" (5 characters).
    scenarios = sorted({t[5:] for t, _ in rows})
    for sid in scenarios:
        s = load(Path(data_dir) / f"{sid}.json")
        kind = s.variant if s.variant != "none" else "none"
        for e in entries(s):
            row = rows.get((f"task-{sid}", e.id))
            if row is None:
                continue  # the record was not extracted — not part of the evaluation
            part = "update" if e.id.startswith("x-") else "base"
            expected = {(f.entity, f.attribute, f.value) for f in e.oracle_facts}
            got = set() if row["refusal"] else {(f["entity"], f["attribute"], f["value"]) for f in row["facts"]}
            refusals += bool(row["refusal"])
            bucket = out[(kind, part)]
            bucket["tp"] += len(got & expected)
            bucket["fp"] += len(got - expected)
            bucket["fn"] += len(expected - got)
    result = dict(out)
    # Service key (not a tuple), so that render() tells it apart from the table rows.
    result["_refusals"] = refusals
    return result

def render(q: dict) -> str:
    """Table in Markdown: precision and recall for each group."""
    lines = ["| kind of update | part | expected | found | wrong | missed | precision | recall |", "|---|---|---|---|---|---|---|---|"]
    for key in sorted(k for k in q if isinstance(k, tuple)):
        c = q[key]
        # precision = tp/(tp+fp): the share of what was found that is correct. recall = tp/(tp+fn): the share of what was expected that was found.
        # If there is nothing to divide — nan, not 0, so that "no data" does not look like "bad".
        p = c["tp"] / (c["tp"] + c["fp"]) if c["tp"] + c["fp"] else float("nan")
        r = c["tp"] / (c["tp"] + c["fn"]) if c["tp"] + c["fn"] else float("nan")
        lines.append(f"| {key[0]} | {key[1]} | {c['tp'] + c['fn']} | {c['tp']} | {c['fp']} | {c['fn']} | {p:.3f} | {r:.3f} |")
    lines.append(f"\nRefused extractions: {q['_refusals']}. Their facts count as missed.")
    return "\n".join(lines) + "\n"

def main() -> None:
    if len(sys.argv) != 3:
        sys.exit("usage: extraction_quality.py <cache.jsonl> <data-dir>")
    print(render(quality(sys.argv[1], sys.argv[2])), end="")

if __name__ == "__main__":
    main()
