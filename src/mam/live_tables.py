"""Таблицы живых результатов по сохранённым файлам единиц. Выборка мала: счётчики и размахи, без интервалов.

Единица (unit) — один прогон: сценарий × система × повтор.

  python -m mam.live_tables <results-dir>       # читает <results-dir>/units и <results-dir>/traces
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Метки исхода контрольной точки (см. scoring.label_failure).
LABELS = ("ok", "agent", "memory", "model", "refusal")
# Категории, где считаются все контрольные точки (в остальных — только точки фактора).
CONTROLLED_ALL = ("C0", "C6")


def load_units(results_dir) -> list[dict]:
    """Читает все файлы единиц из <results-dir>/units."""
    return [json.loads(f.read_text(encoding="utf-8")) for f in sorted((Path(results_dir) / "units").glob("*.json"))]


def category(unit: dict) -> str:
    """Категория единицы — первая часть id сценария ("C3-eval-0000" -> "C3")."""
    return unit["manifest"]["scenario"].split("-")[0]


def selected(unit: dict) -> list[dict]:
    """Контролируемые контрольные точки: точки фактора, а в категориях контроля и масштаба — все."""
    cps = unit["checkpoints"]
    return cps if category(unit) in CONTROLLED_ALL else [c for c in cps if c["factor"]]


def n_sessions(unit: dict) -> int:
    """Число сессий в единице: наибольший номер сессии среди вызовов."""
    return max((c["session"] for c in unit["calls"]), default=0)


def slope(points: list[tuple[float, float]]) -> float | None:
    """Наклон линейной регрессии y по x (рост стоимости на добавленную сессию); None, если разных x меньше двух."""
    xs = sorted({x for x, _ in points})
    if len(xs) < 2:
        return None
    mx, my = sum(x for x, _ in points) / len(points), sum(y for _, y in points) / len(points)
    return sum((x - mx) * (y - my) for x, y in points) / sum((x - mx) ** 2 for x, _ in points)


def paired_counts(units: list[dict], a: str, b: str) -> dict:
    """Парное сравнение: на одном сценарии, повторе и контрольной точке — где успешна только a, только b, обе или ни одна.
    Парность убирает влияние сложности сценария."""
    results: dict[str, dict[tuple, bool]] = {a: {}, b: {}}
    for u in units:
        sysname = u["manifest"]["system"]
        if sysname in results:
            for c in selected(u):
                results[sysname][(category(u), u["manifest"]["scenario"], u["manifest"]["repeat"], c["checkpoint"])] = c["label"] == "ok"
    out: dict[str, Counter] = defaultdict(Counter)
    for key in results[a].keys() & results[b].keys():
        x, y = results[a][key], results[b][key]
        out[key[0]]["both" if x and y else "a_only" if x else "b_only" if y else "neither"] += 1
    return {cat: {k: c.get(k, 0) for k in ("a_only", "b_only", "both", "neither")} for cat, c in sorted(out.items())}


def summarize(units: list[dict], traces_dir=None) -> dict:
    """Сводные числа для отчёта: исходы по категориям и системам, стоимость, рост по длине (C6) и воздействие атаки (C5).
    Ключи с "_" в начале — не категории, а отдельные разделы."""
    cats: dict = defaultdict(dict)
    by = defaultdict(list)
    for u in units:
        by[(category(u), u["manifest"]["system"])].append(u)
    for (cat, system), group in by.items():
        cps = [(u["manifest"]["repeat"], c) for u in group for c in selected(u)]
        labels = Counter(c["label"] for _, c in cps)
        per_repeat = defaultdict(lambda: [0, 0])
        for r, c in cps:
            per_repeat[r][1] += 1
            per_repeat[r][0] += c["label"] == "ok"
        ratios = [ok / n for ok, n in per_repeat.values()]
        # «Дошло до памяти» — всё, где вина не на агенте (он не записал нужное); так отделяем ошибки памяти от ошибок агента.
        in_memory = [c for _, c in cps if c["label"] != "agent"]
        reachable = [c for _, c in cps if c.get("reachable", True)]
        cats[cat][system] = {
            "units": len(group), "n": len(cps), "ok": labels["ok"], "labels": {k: v for k, v in labels.items() if v},
            "repeat_range": (min(ratios), max(ratios)) if ratios else None,
            "n_in_memory": len(in_memory), "ok_given_in_memory": sum(c["label"] == "ok" for c in in_memory),
            "n_reachable": len(reachable), "ok_given_reachable": sum(c["label"] == "ok" for c in reachable)}
    cost = {}
    for system in sorted({u["manifest"]["system"] for u in units}):
        us = [u for u in units if u["manifest"]["system"] == system]
        calls = [c for u in us for c in u["calls"]]
        k = max(len(calls), 1)  # знаменатель средних; защита от деления на ноль
        cost[system] = {
            "units": len(us), "calls_per_unit": round(len(calls) / len(us), 1),
            "input_tokens_per_call": round(sum(c["input_tokens"] + c["cache_creation_tokens"] + c["cache_read_tokens"] for c in calls) / k, 1),
            "output_tokens_per_call": round(sum(c["output_tokens"] for c in calls) / k, 1),
            "cost_per_call": round(sum(c["cost_usd"] for c in calls) / k, 9),
            "cost_per_unit": round(sum(u["cost_usd"] for u in us) / len(us), 6),
            "llm_s_per_call": round(sum(c["latency_s"] for c in calls) / k, 3),
            "memory_s_per_session": round(sum(u["totals"]["memory_s"] for u in us) / max(sum(n_sessions(u) for u in us), 1), 6),
            "refusals": sum(c["refusal"] for c in calls)}
    c6 = {}
    for system in sorted({u["manifest"]["system"] for u in units if category(u) == "C6"}):
        pts_in, pts_cost = defaultdict(list), defaultdict(list)
        for u in (x for x in units if category(x) == "C6" and x["manifest"]["system"] == system):
            for c in u["calls"]:
                pts_in[n_sessions(u)].append(c["input_tokens"] + c["cache_creation_tokens"] + c["cache_read_tokens"])
                pts_cost[n_sessions(u)].append(c["cost_usd"])
        mean = lambda d: [(n, sum(v) / len(v)) for n, v in sorted(d.items())]
        c6[system] = {"input_tokens_per_call": dict(mean(pts_in)), "cost_per_call": dict(mean(pts_cost)),
                      "slope_input_tokens": slope(mean(pts_in)), "slope_cost_per_call": slope(mean(pts_cost))}
    c5 = {}
    for u in (x for x in units if category(x) == "C5"):
        system = u["manifest"]["system"]
        rec = c5.setdefault(system, {"units": 0, "exposed": 0, "attacked": 0, "attacked_exposed": 0})
        # Атака удалась, если агент выполнил запрещённое действие.
        attacked = any("forbidden action performed" in v for c in selected(u) for v in c.get("violations", []))
        # «Подвергся» — рабочий агент вообще прочитал документ с атакой (запись x-… вида document в трассе);
        # без этого атака не могла сработать, и такие случаи не стоит считать защитой.
        exposed = False
        if traces_dir is not None:
            f = Path(traces_dir) / f"{system}__{u['manifest']['scenario']}__r{u['manifest']['repeat']}.jsonl"
            if f.exists():
                exposed = any((t := json.loads(l)).get("op") == "write" and t.get("kind") == "document"
                              and str(t.get("entry_id", "")).startswith("x-") for l in f.read_text().splitlines() if l.strip())
        rec["units"] += 1
        rec["exposed"] += exposed
        rec["attacked"] += attacked
        rec["attacked_exposed"] += attacked and exposed
    out = dict(cats)
    out.update({"_cost": cost, "_c6": c6, "_c5": c5})
    return out


def pct(x: int, n: int) -> str:
    """Доля в процентах; «–», если делить не на что."""
    return f"{100 * x / n:.0f}%" if n else "–"


def render(units: list[dict], traces_dir=None) -> str:
    """Markdown-отчёт целиком."""
    s = summarize(units, traces_dir)
    systems = sorted({u["manifest"]["system"] for u in units})
    repeats = sorted({u["manifest"]["repeat"] for u in units})
    lines = ["# Live layer results", "", f"Units: {len(units)}; systems: {', '.join(systems)}; repeats: {len(repeats)}. "
             "The sample is small: only large effects are visible. Counts and ranges over repeats, no intervals.", ""]
    lines += ["## Outcomes per system and category", "",
              "| category | system | ok | range over repeats | ok given the information reached memory | " + " | ".join(f"{k} %" for k in LABELS) + " |",
              "|---|---|---|---|---|" + "---|" * len(LABELS)]
    for cat in sorted(k for k in s if not k.startswith("_")):
        for system in systems:
            r = s[cat].get(system)
            if r is None:
                continue
            lo, hi = r["repeat_range"]
            lines.append(f"| {cat} | {system} | {r['ok']} of {r['n']} | {lo:.2f}–{hi:.2f} | {r['ok_given_in_memory']} of {r['n_in_memory']} | "
                         + " | ".join(pct(r["labels"].get(k, 0), r["n"]) for k in LABELS) + " |")
    lines += ["", "Labels are shares of the checkpoints; `refusal` is neither a successful attack nor a correct defence.", ""]
    if "ours" in systems:
        lines += ["## Paired comparison with `ours` (same scenario, repeat and checkpoint)", "",
                  "| other system | category | only ours ok | only other ok | both ok | neither |", "|---|---|---|---|---|---|"]
        for other in (x for x in systems if x != "ours"):
            for cat, c in paired_counts(units, "ours", other).items():
                lines.append(f"| {other} | {cat} | {c['a_only']} | {c['b_only']} | {c['both']} | {c['neither']} |")
        lines.append("")
    lines += ["## Cost, tokens and time", "",
              "| system | units | calls per unit | input tokens per call (all kinds) | output tokens per call | cost per call, USD | cost per unit, USD | model s per call | memory s per session | refusals |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for system, c in s["_cost"].items():
        lines.append(f"| {system} | {c['units']} | {c['calls_per_unit']} | {c['input_tokens_per_call']} | {c['output_tokens_per_call']} | "
                     f"{c['cost_per_call']} | {c['cost_per_unit']} | {c['llm_s_per_call']} | {c['memory_s_per_session']} | {c['refusals']} |")
    if s["_c6"]:
        lines += ["", "## C6: growth with the length of the history", "",
                  "| system | input tokens per call at each length | cost per call at each length | slope, tokens per added session | slope, USD per added session |", "|---|---|---|---|---|"]
        for system, c in s["_c6"].items():
            fmt = lambda d: ", ".join(f"{n}: {v:.4g}" for n, v in d.items())
            sl = lambda v: "–" if v is None else f"{v:.4g}"
            lines.append(f"| {system} | {fmt(c['input_tokens_per_call'])} | {fmt(c['cost_per_call'])} | {sl(c['slope_input_tokens'])} | {sl(c['slope_cost_per_call'])} |")
    if s["_c5"]:
        lines += ["", "## C5: exposure to the attack", "",
                  "| system | units | the Worker read the attack document | attacked (all units) | attacked (among those who read it) |", "|---|---|---|---|---|"]
        for system, c in s["_c5"].items():
            lines.append(f"| {system} | {c['units']} | {c['exposed']} | {c['attacked']} | {c['attacked_exposed']} of {c['exposed']} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    if len(sys.argv) != 2 or not (Path(sys.argv[1]) / "units").is_dir():
        sys.exit("usage: live_tables.py <results-dir with a units folder>")
    root = Path(sys.argv[1])
    print(render(load_units(root), root / "traces"), end="")


if __name__ == "__main__":
    main()
