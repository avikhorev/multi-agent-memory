"""Does the outcome of `ours` depend on the order of writes? Recomputed from the traces of the live run (post hoc).

  python scripts/post_hoc_write_order.py [--traces results/live/main/traces] [--out results/post_hoc/write_order.md]

The facts and the trust of each entry come from the traces of `ours`. A key with more than one value is resolved
twice by the code of `ours`: in the order of the run and in the reverse order. No model is called.
Private versions are left out, as in `Ours.known_lines`: the rest is the state of a shared key after the last session.
"""
import argparse
import collections
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mam.extract import UNKNOWN_TIME  # noqa: E402
from mam.systems.ours import AUTHORITY, TRUST, Ours, Version  # noqa: E402

CATS = ["C0", "C1", "C2", "C3", "C4", "C5", "C6"]
COLUMNS = ["keys", "conflicts", "order_changes_outcome", "all_versions_dated", "untrusted_beats_trusted"]


def load_versions(path):
    writes, facts = {}, []
    for line in path.read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        if rec["op"] == "write":
            writes[rec["entry_id"]] = rec
        elif rec["op"] == "extraction":
            facts.extend((rec["entry_id"], f) for f in rec["facts"])
    keys = {}
    for entry_id, f in facts:
        w = writes[entry_id]
        if w["scope"] == "private":
            continue
        fact = SimpleNamespace(value=f["value"], entity=f["entity"], attribute=f["attribute"], source=f["source"])
        entry = SimpleNamespace(clock=w["clock"], id=entry_id)
        keys.setdefault((f["entity"], f["attribute"]), []).append(
            Version(fact, entry, f["valid_from"], AUTHORITY.get(f["source"], 0), TRUST[w["trust"]]))
    return keys


def reverse_order(versions):
    last = max(v.entry.clock for v in versions) + 1
    return [Version(v.fact, SimpleNamespace(clock=last - v.entry.clock, id=v.entry.id), v.time, v.authority, v.trust)
            for v in versions]


def scan(traces):
    resolver = Ours(limit=2000)
    outcome = lambda versions: {v.fact.value for v in resolver._resolve(versions)}  # noqa: E731
    rows = {c: collections.Counter() for c in CATS}
    for path in sorted(Path(traces).glob("ours__*.jsonl")):
        row = rows[path.stem.split("__")[1][:2]]
        for versions in load_versions(path).values():
            row["keys"] += 1
            if len({v.fact.value for v in versions}) < 2:
                continue
            row["conflicts"] += 1
            now = outcome(versions)
            if now != outcome(reverse_order(versions)):
                row["order_changes_outcome"] += 1
                row["all_versions_dated"] += all(v.time != UNKNOWN_TIME for v in versions)
            trusted = {v.fact.value for v in versions if v.trust == TRUST["trusted"]}
            row["untrusted_beats_trusted"] += bool(trusted) and not now & trusted and all(
                v.trust == TRUST["untrusted"] for v in versions if v.fact.value in now)
    return rows


def table(rows):
    lines = ["# Зависимость итога `ours` от порядка записей", "",
             "Источник: трассы `ours` в `results/live/main/traces`, факты и доверие записей взяты из них.",
             "Записи области `private` не учитываются.",
             "`order_changes_outcome`: итог меняется, если те же версии записать в обратном порядке.",
             "`all_versions_dated`: из них случаи, где у всех версий есть дата события.",
             "`untrusted_beats_trusted`: остаётся недоверенное значение, хотя есть доверенная версия.", "",
             "| Категория | " + " | ".join(COLUMNS) + " |", "|---|" + "---|" * len(COLUMNS)]
    total = collections.Counter()
    for cat in CATS:
        total.update(rows[cat])
        lines.append(f"| {cat} | " + " | ".join(str(rows[cat][c]) for c in COLUMNS) + " |")
    lines.append("| всего | " + " | ".join(str(total[c]) for c in COLUMNS) + " |")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--traces", default=str(ROOT / "results/live/main/traces"))
    ap.add_argument("--out", default=str(ROOT / "results/post_hoc/write_order.md"))
    args = ap.parse_args()
    text = table(scan(args.traces))
    Path(args.out).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
