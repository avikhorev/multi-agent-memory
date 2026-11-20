"""Таблицы результатов уровня памяти с бутстреп-интервалами по сценариям.

  python -m mam.tables <results-dir> [--title "..."]
"""
from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

from mam.memory_eval import systems_for
from mam.scoring import is_controlled

BOOTSTRAP = 2000  # число бутстреп-повторов для доверительного интервала
SEED = 12345  # фиксированное зерно: интервалы воспроизводимы

# Метрики: (категория, подпись, функция значения по записи контрольной точки, ключ группировки или None).
METRICS = [
    ("C0", "correct", lambda r: r["passed"], None),
    ("C1", "current value present", lambda r: r["missing_present"] == 0, "variant"),
    ("C1", "stale value shown", lambda r: r["stale_present"], "variant"),
    ("C2", "constraint in context", lambda r: r["passed"], None),
    ("C3", "resolved correctly", lambda r: r["passed"], "resolution"),
    ("C4", "foreign private item in context", lambda r: r["foreign_private_present"], None),
    ("C4", "public facts present", lambda r: r["missing_present"] == 0, None),
    ("C5", "attack in instruction slot", lambda r: r["attack_in_instruction_slot"], None),
    ("C5", "legitimate item blocked", lambda r: r["missing_present"] > 0, None),
    ("C6", "correct", lambda r: r["passed"], "n_sessions"),
    ("C6", "context tokens (mean)", lambda r: r["token_count"], "n_sessions"),
]


def load_results(directory: Path) -> dict[str, list[dict]]:
    """Читает все <система>.jsonl каталога: имя файла без расширения -> список записей."""
    out = {}
    for p in sorted(directory.glob("*.jsonl")):
        out[p.stem] = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    return out


def interval(values: list[float]) -> tuple[float, float, float]:
    """(среднее, нижняя, верхняя граница 95% интервала) бутстрепом по значениям (по одному на сценарий)."""
    rng = random.Random(SEED)
    mean = sum(values) / len(values)
    means = sorted(sum(rng.choice(values) for _ in values) / len(values) for _ in range(BOOTSTRAP))
    return mean, means[int(0.025 * BOOTSTRAP)], means[int(0.975 * BOOTSTRAP) - 1]


def per_scenario(rows: list[dict], category: str, fn, group: str | None) -> dict[str, list[float]]:
    """Группа -> список значений метрики, по одному на сценарий (среднее по его контрольным точкам).
    Усреднение по сценарию нужно, чтобы сценарий с большим числом точек не перевешивал остальные."""
    by = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r.get("record") != "checkpoint" or r["category"] != category:
            continue
        if not is_controlled(category, r["factor"]):
            continue  # в категориях с фактором считаем только его точки
        by[str(r[group]) if group else "all"][r["scenario"]].append(float(fn(r)))
    return {g: [sum(v) / len(v) for v in sc.values()] for g, sc in by.items()}


def render(results: dict[str, list[dict]], title: str = "") -> str:
    """Markdown со всеми таблицами; системы идут в известном порядке, неизвестные — в конце."""
    known = systems_for(True)
    systems = [s for s in known if s in results] + [s for s in results if s not in known]
    lines = [f"# {title}".rstrip(), ""] if title else []
    for category in ("C0", "C1", "C2", "C3", "C4", "C5", "C6"):
        for cat, label, fn, group in METRICS:
            if cat != category:
                continue
            data = {s: per_scenario(results[s], cat, fn, group) for s in systems}
            groups = sorted({g for d in data.values() for g in d}, key=lambda g: (len(g), g))
            lines += [f"### {cat}: {label}", "", "| system | " + " | ".join(
                (f"{group}={g}" if group else "all") + " (n=%d)" % len(next((d[g] for d in data.values() if g in d), []))
                for g in groups) + " |", "|---|" + "---|" * len(groups)]
            for s in systems:
                cells = []
                for g in groups:
                    vals = data[s].get(g)
                    if not vals:
                        cells.append("–")
                        continue
                    m, lo, hi = interval(vals)
                    cells.append(f"{m:.0f} [{lo:.0f}, {hi:.0f}]" if "tokens" in label else f"{m:.2f} [{lo:.2f}, {hi:.2f}]")
                lines.append(f"| {s} | " + " | ".join(cells) + " |")
            lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("results_dir")
    ap.add_argument("--title", default="")
    a = ap.parse_args()
    print(render(load_results(Path(a.results_dir)), a.title))


if __name__ == "__main__":
    main()
