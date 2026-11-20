"""Which scenarios the live layer runs: a fixed rule over the manifest, applied before any run.

The rule is set in advance, not chosen by the results, so that the choice does not depend on
how the system showed itself (otherwise it would be overfitting).
"""
from __future__ import annotations

import json

# How many scenarios to take from each category for each run size.
PER_CATEGORY = {"smoke": 1, "B": 2, "A": 3}
# For smoke, in category C6 take the scenario of 10 sessions (the shortest).
FIRST_TEN = 10

def select_live(manifest_path, size: str) -> list[str]:
    """smoke: one per category (C6 on 10 sessions); B: 2 per category; A: 3.

    In C1 and C3 both kinds of updates are kept: in A two implicit and one explicit, in B one of each.
    In C6 take one scenario of each length (10, 20, 30) in A and B.
    Returns the list of scenario ids in category order.
    """
    scenarios = json.load(open(manifest_path))["scenarios"]
    # Group the manifest scenarios by category, keeping the order inside a category.
    by_cat: dict[str, list[dict]] = {}
    for s in scenarios:
        by_cat.setdefault(s["category"], []).append(s)
    n = PER_CATEGORY[size]
    picked: list[str] = []
    for cat in ("C0", "C1", "C2", "C3", "C4", "C5"):
        pool = by_cat[cat]
        if cat in ("C1", "C3") and size != "smoke":
            # We want both implicit and explicit updates: n-1 implicit + 1 explicit.
            implicit = [s for s in pool if s["variant"] == "implicit"][: n - 1]
            explicit = [s for s in pool if s["variant"] == "explicit"][:1]
            picked += [s["id"] for s in implicit + explicit]
        else:
            picked += [s["id"] for s in pool[:n]]
    # C6 — a check on length: a separate scenario for each length of history.
    c6 = by_cat["C6"]
    lengths = (FIRST_TEN,) if size == "smoke" else (10, 20, 30)
    for length in lengths:
        picked.append(next(s["id"] for s in c6 if s["n_sessions"] == length))
    return picked
