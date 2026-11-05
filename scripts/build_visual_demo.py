"""Build the read-only visual replay from committed live runs.

No model calls, external dependencies, or changes to results/. The browser uses
this generated JS file directly, so docs/demo/index.html also works via file://.

    python3 scripts/build_visual_demo.py          # regenerate docs/demo/data.js
    python3 scripts/build_visual_demo.py --check  # fail if it is out of date
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "docs/demo/data.js"

# These are selected checkpoints of the *frozen* live run, repeat 0. The copy
# here describes the tour; all empirical values are taken from JSON/JSONL.
CASES = (
    {
        "id": "c1-update",
        "scenario": "C1-eval-0000",
        "checkpoint": "cpx-1",
        "focus_events": ("e-0017", "x-0001"),
        "worker_session": 5,
        "title": "Устаревшее значение",
        "short": "C1 · обновление",
        "description": "Документ задаёт резерв 727 000 USD; затем пользователь обновляет его до 153 000 USD. Что увидит Planner?",
        "source_note": "Здесь важны два события в разных сессиях: документ и доверенное сообщение пользователя.",
        "memory_note": "У ours есть извлечение и разрешение версий; full_history хранит записи без разрешения конфликта.",
        "agent_note": "Сначала Worker выбирал инструмент в сессии с документом. Позже Planner ответил на вопрос о текущем значении.",
        "result_note": "Старое число в ответе запрещено строгой проверкой, даже если там встречается и новое.",
    },
    {
        "id": "c6-document",
        "scenario": "C6-eval-0002",
        "checkpoint": "cp-1",
        "focus_events": ("e-0002",),
        "worker_session": 1,
        "title": "Пропущенный документ",
        "short": "C6 · документ",
        "description": "Источник с датой UAT был доступен Worker в сессии 1, но вопрос появился только в сессии 28.",
        "source_note": "Предложенный инструмент не означает выполненное чтение: ищите write нужного event_id.",
        "memory_note": "Если Worker не вызвал read_document, событие не поступает в память. Это не ошибка извлечения уже прочитанного факта.",
        "agent_note": "Сравните фактический выбор инструмента в сессии 1 и ответ Planner в сессии 28.",
        "result_note": "Метка agent здесь следует из отсутствия записи обязательного источника; она не доказывает, почему Worker выбрал другой инструмент.",
    },
    {
        "id": "c6-status",
        "scenario": "C6-eval-0002",
        "checkpoint": "cp-3",
        "focus_events": ("e-0086",),
        "worker_session": 27,
        "title": "Пропущенный статус",
        "short": "C6 · статус",
        "description": "Сумма бюджета была доступна через read_status в сессии 27; Reviewer запросил её в сессии 30.",
        "source_note": "Источник — ответ инструмента read_status, не пользовательское сообщение.",
        "memory_note": "Отсутствующий write нельзя компенсировать разрешением конфликтов: входных данных нет.",
        "agent_note": "Сравните действия Worker в сессии 27 и ответ Reviewer в сессии 30.",
        "result_note": "Неуспех может быть вызван поведением агента до записи памяти. Сравнение не изолирует влияние выбора инструментов.",
    },
)
SYSTEMS = ("ours", "full_history")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def in_context(item_id: str, entry_id: str) -> bool:
    """Match source entry IDs only, not loose substrings (e-0002 vs e-00020)."""
    return item_id == f"raw-{entry_id}" or item_id.endswith(f"-{entry_id}") or f"-{entry_id}-" in item_id


def build_bundle(root: Path = ROOT) -> dict:
    """Generate compact, inspectable evidence; never synthesize missing context text."""
    scenarios = {c["scenario"]: load_json(root / "data/eval" / f"{c['scenario']}.json") for c in CASES}
    traces = {}
    units = {}
    for scenario_id in scenarios:
        for system in SYSTEMS:
            prefix = f"{system}__{scenario_id}__r0"
            traces[scenario_id, system] = load_jsonl(root / "results/live/main/traces" / f"{prefix}.jsonl")
            units[scenario_id, system] = load_json(root / "results/live/main/units" / f"{prefix}.json")

    cases = []
    for case in CASES:
        scenario_id, checkpoint_id = case["scenario"], case["checkpoint"]
        scenario = scenarios[scenario_id]
        cp = next(c for c in scenario["checkpoints"] if c["id"] == checkpoint_id)
        events = {e["id"]: {**e, "session": session["index"]}
                  for session in scenario["sessions"] for e in session["events"]}
        focus_events = []
        for entry_id in case["focus_events"]:
            event = events[entry_id]
            focus_events.append({
                "id": entry_id,
                "session": event["session"],
                "type": event["type"],
                "author": event["author"],
                "tool": event["tool"],
                "args": event["args"],
                "text": event["text"],
            })

        record = {k: v for k, v in case.items() if k != "focus_events"}
        record["focus_events"] = focus_events
        record["question"] = {
            "text": cp["task_text"],
            "expected": cp["answer"]["expect"],
            "stale": cp["answer"].get("stale", []),
            "role": cp["role"],
            "session": cp["session"],
        }
        record["files"] = {"scenario": f"data/eval/{scenario_id}.json"}
        record["systems"] = {}
        for system in SYSTEMS:
            trace = traces[scenario_id, system]
            unit = units[scenario_id, system]
            checkpoint = next(c for c in unit["checkpoints"] if c["checkpoint"] == checkpoint_id)
            # The trace itself must agree with the scored unit. A visual replay
            # cannot silently display a label from a different checkpoint/run.
            trace_checks = [r for r in trace if r["op"] == "check" and r["checkpoint_id"] == checkpoint_id]
            trace_labels = [r for r in trace if r["op"] == "label" and r["checkpoint_id"] == checkpoint_id]
            assert len(trace_checks) == len(trace_labels) == 1, (system, checkpoint_id)
            assert trace_checks[0]["passed"] == checkpoint["passed"]
            assert trace_labels[0]["label"] == checkpoint["label"]
            actions = [r for r in trace if r["op"] == "agent_action"
                       and r["role"] == cp["role"] and r["session"] == cp["session"]]
            assert len(actions) == 1 or (cp["role"] == "worker" and actions), (system, checkpoint_id)
            action = actions[0]
            reads = [r for r in trace if r["op"] == "read"
                     and r["reader"] == cp["role"] and r["clock"] == action["clock"]]
            assert len(reads) == 1, (system, checkpoint_id, "read not found")
            read = reads[0]
            assert read["token_count"] == checkpoint["token_count"]
            assert action["answer"] == checkpoint["answer"]
            writes = {r["entry_id"]: r for r in trace if r["op"] == "write"}
            extractions = {r["entry_id"]: r for r in trace if r["op"] == "extraction"}
            observed = {}
            for event in focus_events:
                entry_id = event["id"]
                matched = [item_id for item_id in read["item_ids"] if in_context(item_id, entry_id)]
                written = writes.get(entry_id)
                extracted = extractions.get(entry_id)
                observed[entry_id] = {
                    "written": written is not None,
                    "trust": written["trust"] if written else None,
                    "facts": extracted["facts"] if extracted else [],
                    "context_ids": matched,
                }
                if matched:
                    assert written is not None, (system, checkpoint_id, entry_id)
            related_values = {cp["answer"]["expect"], *cp["answer"].get("stale", [])}
            resolves = [{"winner": r["winner"], "loser": r["loser"], "rule": r["rule"]}
                        for r in trace if r["op"] == "resolve"
                        and (r["winner"] in related_values or r["loser"] in related_values)]
            worker_actions = [
                {"tool": r["tool"], "args": r["args"], "answer": r["answer"], "clock": r["clock"]}
                for r in trace if r["op"] == "agent_action" and r["role"] == "worker"
                and r["session"] == case["worker_session"]
            ]
            assert len(worker_actions) == 2, (system, case["worker_session"])
            record["systems"][system] = {
                "sources": observed,
                "resolution": resolves,
                "context": {
                    "tokens": read["token_count"],
                    "total_ids": len(read["item_ids"]),
                    # For orientation only: IDs, *not* the full context text.
                    "sample_ids": read["item_ids"][:8],
                },
                "worker_actions": worker_actions,
                "checkpoint": {
                    "answer": checkpoint["answer"],
                    "passed": checkpoint["passed"],
                    "context_passed": checkpoint["context_passed"],
                    "label": checkpoint["label"],
                    "violations": checkpoint["violations"],
                    "reachable": checkpoint["reachable"],
                },
            }
            record["files"][system] = {
                "unit": f"results/live/main/units/{system}__{scenario_id}__r0.json",
                "trace": f"results/live/main/traces/{system}__{scenario_id}__r0.jsonl",
            }
        cases.append(record)
    return {"schema": 1, "run": "results/live/main · repeat r0 · frozen eval", "cases": cases}


def render_js(bundle: dict) -> str:
    # JS is a separate file, not inline HTML; every string is rendered in the
    # browser via textContent. Escaping angle brackets also prevents accidental
    # HTML/script-like payloads from making it into a future embedded copy.
    data = json.dumps(bundle, ensure_ascii=False, sort_keys=True, indent=2)
    return "/* Generated by scripts/build_visual_demo.py; do not edit by hand. */\n" + \
           "window.MAM_DEMO_DATA = " + data.replace("<", "\\u003c") + ";\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify committed demo matches saved evidence")
    args = parser.parse_args()
    expected = render_js(build_bundle())
    if args.check:
        if not DEST.exists() or DEST.read_text(encoding="utf-8") != expected:
            print(f"Outdated {DEST.relative_to(ROOT)}: run python3 scripts/build_visual_demo.py", file=sys.stderr)
            return 1
        print("Visual demo: generated evidence is up to date (3 checkpoints, 2 systems, r0)")
        return 0
    DEST.write_text(expected, encoding="utf-8")
    print(f"Created {DEST.relative_to(ROOT)} ({len(expected.encode('utf-8'))} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
