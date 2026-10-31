"""Which scenarios the live layer runs: a fixed rule over the manifest, applied before any run."""
from __future__ import annotations

import json

PER_CATEGORY = {"smoke": 1, "B": 2, "A": 3}
FIRST_TEN = 10


def select_live(manifest_path, size: str) -> list[str]:
    """smoke: one per category (C6 at 10 sessions); B: 2 per category; A: 3 per category.

    C1 and C3 keep both update kinds: A takes two implicit and one explicit, B one of each.
    C6 takes one scenario per length (10, 20, 30) in A and B.
    """
    scenarios = json.load(open(manifest_path))["scenarios"]
    by_cat: dict[str, list[dict]] = {}
    for s in scenarios:
        by_cat.setdefault(s["category"], []).append(s)
    n = PER_CATEGORY[size]
    picked: list[str] = []
    for cat in ("C0", "C1", "C2", "C3", "C4", "C5"):
        pool = by_cat[cat]
        if cat in ("C1", "C3") and size != "smoke":
            implicit = [s for s in pool if s["variant"] == "implicit"][: n - 1]
            explicit = [s for s in pool if s["variant"] == "explicit"][:1]
            picked += [s["id"] for s in implicit + explicit]
        else:
            picked += [s["id"] for s in pool[:n]]
    c6 = by_cat["C6"]
    lengths = (FIRST_TEN,) if size == "smoke" else (10, 20, 30)
    for length in lengths:
        picked.append(next(s["id"] for s in c6 if s["n_sessions"] == length))
    return picked
