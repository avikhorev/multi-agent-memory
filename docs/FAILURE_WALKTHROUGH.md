# Failure analysis: source not read (C6)

In the [successful C1 example](WALKTHROUGH.md) you can see how an update turns into an answer. Here is the opposite case from the **saved main run**: the agent did not request the proposed source, the needed event was not recorded, and the answer failed the check. No new model calls are required.

**Step by step:** [visual demo of the omission of the document and status](demo/README.md), switching between `ours` and `full_history`.

**Scenario:** [`C6-eval-0002`](../data/eval/C6-eval-0002.json), 30 sessions. **System:** the original `ours`, repeats `r0` and `r1`. The questions arise in sessions 28–30, but some answers depend on much earlier events.

## 1. What data was available

| Check | Expected answer | Where it was | When the question is asked |
|---|---|---|---|
| `cp-1`, Planner | `2026-05-07` — UAT start for `notifications` | `e-0002`, document `D-011`, proposed to the Worker in session **1** | Session **28** |
| `cp-2`, Worker | `Tomas Iyer` — owner of `archive` | `e-0004`, source from an early session | Session **29** |
| `cp-3`, Reviewer | `343000` — budget of `archive` | `e-0086`, the answer of `read_status` in session **27** | Session **30** |

`e-0002` and `e-0086` are tool answers (`tool_data`); `e-0004` is a user message in session 2, which is written to memory without any action by the Worker. **A proposed source is not the same as a read one:** the runner gives the Worker a description of the available tool, and a `Entry` record appears only after the corresponding `read_document` or `read_status` ([`live.py`](../src/mam/live.py), [`Simulator`](../src/mam/simulate.py)). The checkpoint names the needed source in `required_events`.

## 2. What happened in `ours`

On the first call of the Worker in session 1 it chose `update_record`, not `read_document(D-011)`; in session 27 it again chose `update_record` instead of `read_status(Atlas/archive)`. This can be seen in the [`r0` trace](../results/live/main/traces/ours__C6-eval-0002__r0.jsonl) and the [`r1` trace](../results/live/main/traces/ours__C6-eval-0002__r1.jsonl).

| Check | `ours`, r0 | `ours`, r1 |
|---|---|---|
| `cp-1`: UAT start | Not passed; `agent`, the context is wrong | Not passed; `agent`, the context is wrong |
| `cp-2`: owner | Passed; `ok` | Passed; `ok` |
| `cp-3`: budget | Not passed; `agent`, the context is wrong | Not passed; `agent`, the context is wrong |

Both repeats contain no `write` operation for `e-0002` and `e-0086`, but they do contain the record `e-0004`. That is why `cp-2` passes, while on `cp-1` the Planner says that the specific date for `notifications` is missing; on `cp-3` the Reviewer does not find the budget of `archive`. Storage of the missed document cannot be checked here itself: **the document did not reach memory**.

## 3. How the label `agent` is assigned

On both failed checks `reachable = true`: the original event was available in the scenario. However, `written_event_ids` contains none of the events from `required_events` of the corresponding checkpoint. The function [`label_failure`](../src/mam/scoring.py) first checks `refusal` and the success of the action, then the absence of a record of the required event — and **before checking the quality of the context** it returns `agent`.

Thus `agent` is **a label according to the algorithm**, not an established psychological cause of the tool choice. `context_passed = false` is also correct here: the needed value is not in memory. But this does not prove that the `ours` implementation stored an already received fact incorrectly.

For contrast, [`full_history`, r0](../results/live/main/units/full_history__C6-eval-0002__r0.json) and [`r1`](../results/live/main/units/full_history__C6-eval-0002__r1.json) read both sources: `cp-1` and `cp-3` passed. At the same time `full_history` in `r0` **did not pass** another check — `cp-2` (`model`, a wrong answer with a correct context). One successful reading of a source does not mean better behavior on all questions.

## 4. Check on the saved data

From the repository root, Python 3.11+, without the LLM and without changing files:

```bash
python3 - <<'PY'
import json
from pathlib import Path

scenario = "C6-eval-0002"
for system in ("ours", "full_history"):
    for repeat in (0, 1):
        name = f"{system}__{scenario}__r{repeat}"
        unit = json.loads((Path("results/live/main/units") / f"{name}.json").read_text())
        trace = [json.loads(line) for line in
                 (Path("results/live/main/traces") / f"{name}.jsonl").read_text().splitlines()]
        written = {row.get("entry_id") for row in trace if row.get("op") == "write"}
        outcomes = {row["checkpoint"]: row["label"] for row in unit["checkpoints"]}
        print(system, repeat,
              "read D-011:", "e-0002" in written,
              "read STATUS:", "e-0086" in written,
              "labels:", outcomes)
PY
```

Expected signs: for both `ours` — `False`, `False` and `agent` for `cp-1`, `cp-3`; for both `full_history` — `True`, `True` and `ok` for these two checkpoints. If you need the exact text of the answer, look at `checkpoints[].answer` and `violations` in the same files of `units/`.

## 5. How to interpret

This case explains part of the C6 result: `ours` got **12/18** of the selected live checks against **15/18** for `full_history` ([E4](EVIDENCE.md#e4), [section 8 of the report](../REPORT.md#8-failure-analysis)). It shows the chain "tool not called → source not recorded → context incomplete → answer wrong" under this protocol of four model calls per session. It does **not** isolate the cause of the tool choice, and does not establish how the systems would behave under forced reading or under a longer agent cycle.

The mapping of the labels `agent`, `memory`, `model` and the limitations of the classification — in the [evaluation rules](SCENARIO_FORMAT.md#failure-labels) and the [issue register](KNOWN_ISSUES.md#agent-protocol).
