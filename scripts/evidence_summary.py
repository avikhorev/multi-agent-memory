"""Summarize the frozen evaluation data without LLM calls or changing files.

Usage: python3 scripts/evidence_summary.py [--verify]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEMORY_SYSTEMS = (
    "ours@cache", "full_history", "shared_rag_bm25", "rolling_summary@cache", "sliding_window"
)
LIVE_SYSTEMS = ("ours", "rolling_summary", "shared_rag_bm25", "full_history", "sliding_window")
EXPECTED_MEMORY = {"ours@cache": 778, "full_history": 700, "shared_rag_bm25": 700,
                   "rolling_summary@cache": 697, "sliding_window": 660}
EXPECTED_LIVE = {"ours": 124, "rolling_summary": 119, "shared_rag_bm25": 117,
                 "full_history": 108, "sliding_window": 104}


def memory_counts(root: Path) -> dict[str, tuple[int, int]]:
    result = {}
    for system in MEMORY_SYSTEMS:
        filename = root / "results/memory_level/eval" / f"{system}.jsonl"
        passed = total = 0
        with filename.open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                if row.get("record") == "checkpoint":
                    total += 1
                    passed += bool(row["passed"])
        result[system] = (passed, total)
    return result


def live_counts(root: Path) -> dict[str, tuple[int, int, int]]:
    base = root / "results/live/main/units"
    result = {}
    for system in LIVE_SYSTEMS:
        passed = total = 0
        paths = sorted(base.glob(f"{system}__*__r*.json"))
        for path in paths:
            unit = json.loads(path.read_text(encoding="utf-8"))
            if unit["system"] != system:
                raise ValueError(f"Wrong system in {path}")
            checks = unit["checkpoints"]
            total += len(checks)
            passed += sum(bool(check["passed"]) for check in checks)
        result[system] = (passed, total, len(paths))
    return result


def verify(memory: dict, live: dict) -> list[str]:
    errors = []
    for system, (passed, total) in memory.items():
        if (passed, total) != (EXPECTED_MEMORY[system], 780):
            errors.append(f"memory {system}: {passed}/{total}, expected {EXPECTED_MEMORY[system]}/780")
    for system, (passed, total, units) in live.items():
        if (passed, total, units) != (EXPECTED_LIVE[system], 156, 42):
            errors.append(f"live {system}: {passed}/{total} ({units} units), "
                          f"expected {EXPECTED_LIVE[system]}/156 (42 units)")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="check frozen baseline totals")
    args = parser.parse_args()
    try:
        memory = memory_counts(ROOT)
        live = live_counts(ROOT)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Cannot read saved results: {exc}\n")
    print("Memory-level eval (all checkpoints):")
    for system, (passed, total) in memory.items():
        print(f"  {system}: {passed}/{total}")
    print("Live main (all checkpoints, not only factors):")
    for system, (passed, total, units) in live.items():
        print(f"  {system}: {passed}/{total} ({units} units)")
    if args.verify:
        errors = verify(memory, live)
        if errors:
            print("Frozen-data mismatch:\n  " + "\n  ".join(errors))
            return 1
        print("Frozen main-run totals: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
