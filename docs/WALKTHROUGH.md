# From event to answer: one C1 scenario

This is an analysis of a **saved** run, not an idealized demonstration. On the example of `C1-eval-0000` it shows how `ours` replaces an old value with a new one, what the Planner reads, and why the two systems get different scores. All links below point to files in this repository.

**Step by step:** [visual C1 demo with a switch between systems](demo/README.md). It takes the answers and operations from the same files.

**First:** [session diagram](ARCHITECTURE.md#2-one-session) · [scenario format](SCENARIO_FORMAT.md#3-scenario) · [evaluation rules](SCENARIO_FORMAT.md#7-evaluation).

## 1. Source: reserve of 727,000 USD

In the [scenario `C1-eval-0000`](../data/eval/C1-eval-0000.json) session 5 contains the event `e-0017`: the Worker can read the document `D-051` with the reserve `Atlas/search.contingency_usd = 727000`. This is an **untrusted data source**, not an instruction.

In the [`ours` trace, repeat 0](../results/live/main/traces/ours__C1-eval-0000__r0.jsonl) you can see that the document was indeed read and written to memory (`write`, `entry_id=e-0017`, `trust=untrusted`). After the session ends, the extractor records the fact:

```text
Atlas/search | contingency_usd | 727000 | source=document
```

This is a brief record of the fields from the trace, **not the verbatim text of the context**.

## 2. Update from the user: 153,000 USD

In session 6 the user reports (`x-0001`):

> Update: the contingency reserve for the search module is now USD 153,000, it was USD 727,000.

In the [reference facts of the scenario](../data/eval/C1-eval-0000.json) the new value `fx-0001` replaces `fa-0013`. In the live [`ours` trace](../results/live/main/traces/ours__C1-eval-0000__r0.jsonl) the message is recorded with `trust=trusted`; at `end_session(6)` the extractor saved `153000` with the source `user`.

**An important detail:** the reference sets the times `valid_from=30` and `40`, but the records extracted by the model in this trace have `valid_from=-1` (unknown time). Therefore in this case `ours` relies on the **order of writing**, not on the extracted calendar date; see [`Ours._resolve`](../src/mam/systems/ours.py) and the [order limitation](KNOWN_ISSUES.md#order-dependence).

## 3. What gets into memory and the context

After each session, `end_session` calls the extraction. On the next `context(reader)` the memory:

1. keeps only the records visible to the reader;
2. groups the facts by `(entity, attribute)`;
3. resolves the versions taking into account time, trust and authority;
4. selects the current facts and fragments within the limit of 2,000 tokens.

For the key `Atlas/search / contingency_usd` this gives an **approximate representation** of the current fact:

```text
Atlas/search contingency_usd: 153000
```

This is the format from [`_fact_items`](../src/mam/systems/ours.py), not context copied from a live unit. The saved live traces do **not store the context in full**; they record only the identifiers of the items and the number of tokens. The exact string at the memory level can be obtained by repeating the computation without the agent with the saved cache (`make memory-level SPLIT=eval`).

For `full_history` the history stores both the old document and the new message. The system does not perform version resolution: the agent decides which fact is current.

## 4. Checkpoint: Planner, session 7

[Checkpoint `cpx-1`](../data/eval/C1-eval-0000.json) asks the question:

> What is the current contingency reserve for the search module?

The expected answer is `153000`, and `727000` is considered stale and **must not appear in the answer**. The scenario also checks that the old value is absent from the context. This is an intentionally strict criterion, not a universal assessment of the usefulness of the answer.

| System and repeat | Planner's answer from the saved unit | Evaluation |
|---|---|---|
| [`ours`, r0](../results/live/main/units/ours__C1-eval-0000__r0.json) | `The current contingency reserve for the search module is 153000 USD.` | `passed=true`, `label=ok` |
| [`full_history`, r0](../results/live/main/units/full_history__C1-eval-0000__r0.json) | `USD 727,000 per D-051; the 153,000 change is unverified.` | `passed=false`, `label=memory` |
| [`full_history`, r1](../results/live/main/units/full_history__C1-eval-0000__r1.json) | `The current search module contingency reserve is USD 153,000, updated from USD 727,000.` | `passed=false`, `label=memory` |

Note **r1**: the agent named the correct current value but also mentioned the old one. The strict check counted it as a failure. Therefore the difference between `ours` and `full_history` on C1 cannot be read as a difference in the models' ability to understand updates without additional caveats. The analysis of this effect is in [section 6 of the report](../REPORT.md#6-live-layer-results) and in the [evidence](EVIDENCE.md#e3).

## 5. Where the evaluation happens

[`run_live`](../src/mam/live.py) records the events, calls the roles and saves the answers. [`score_context` and `score_action`](../src/mam/scoring.py) check the text of the context and the answer; [`label_failure`](../src/mam/scoring.py) assigns the label. The saved unit contains the fields `checkpoint`, `answer`, `context_passed`, `passed`, `label`, `violations`. The `violations` list of both failures of `full_history` contains `answer contains stale value: 727000`.

You can check a specific answer without the model:

```bash
python3 - <<'PY'
import json
for system in ('ours', 'full_history'):
    path = f'results/live/main/units/{system}__C1-eval-0000__r0.json'
    unit = json.load(open(path, encoding='utf-8'))
    cp = next(x for x in unit['checkpoints'] if x['checkpoint'] == 'cpx-1')
    print(system, cp['answer'], cp['passed'], cp['violations'])
PY
```

## 6. What the example shows and what it does not

**It shows:** the path from the source and the update to recording the fact, preparing the answer and the fixed evaluation rule. The trace confirms that both events reached `ours`.

**It does not show:** that the Worker always reads the documents, that the extraction is robust to free-form wording, or that the strict count means the best practical solution. On C6 the Worker sometimes does not read the proposed source at all, and a defect in action evaluation was found on rephrased rules. These cases are described separately in the [limitations](KNOWN_ISSUES.md).
