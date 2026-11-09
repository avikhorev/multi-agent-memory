"""Какие сценарии запускает живой слой: фиксированное правило по манифесту, применяется до любого запуска.

Правило задано заранее, а не подбирается по результатам, чтобы выбор не зависел от
того, как система себя показала (иначе выйдет подгонка).
"""
from __future__ import annotations

import json

# Сколько сценариев брать из каждой категории для каждого размера прогона.
PER_CATEGORY = {"smoke": 1, "B": 2, "A": 3}
# Для smoke в категории C6 берём сценарий на 10 сессий (самый короткий).
FIRST_TEN = 10

def select_live(manifest_path, size: str) -> list[str]:
    """smoke: по одному на категорию (C6 на 10 сессиях); B: по 2 на категорию; A: по 3.

    В C1 и C3 сохраняются оба вида обновлений: в A два неявных и одно явное, в B по одному.
    В C6 берётся по одному сценарию каждой длины (10, 20, 30) в A и B.
    Возвращает список id сценариев в порядке категорий.
    """
    scenarios = json.load(open(manifest_path))["scenarios"]
    # Группируем сценарии манифеста по категории, порядок внутри категории сохраняем.
    by_cat: dict[str, list[dict]] = {}
    for s in scenarios:
        by_cat.setdefault(s["category"], []).append(s)
    n = PER_CATEGORY[size]
    picked: list[str] = []
    for cat in ("C0", "C1", "C2", "C3", "C4", "C5"):
        pool = by_cat[cat]
        if cat in ("C1", "C3") and size != "smoke":
            # Хотим и неявные, и явные обновления: n-1 неявных + 1 явное.
            implicit = [s for s in pool if s["variant"] == "implicit"][: n - 1]
            explicit = [s for s in pool if s["variant"] == "explicit"][:1]
            picked += [s["id"] for s in implicit + explicit]
        else:
            picked += [s["id"] for s in pool[:n]]
    # C6 — проверка на длине: отдельный сценарий на каждую длину истории.
    c6 = by_cat["C6"]
    lengths = (FIRST_TEN,) if size == "smoke" else (10, 20, 30)
    for length in lengths:
        picked.append(next(s["id"] for s in c6 if s["n_sessions"] == length))
    return picked
