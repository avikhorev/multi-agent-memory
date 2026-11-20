# Evidence for the main conclusions

This collects **verifiable claims**, not another retelling of the report. The summary numbers from [`RESULTS.md`](RESULTS.md) can be matched against the saved data, the recalculation method can be seen, and the remaining limitations can be understood.

## How to check

Commands are run from the repository root. Without the model and without overwriting the results:

```bash
python3 scripts/evidence_summary.py --verify
```

The command reads the lines `record=checkpoint` in `results/memory_level/eval/*.jsonl` and the `checkpoints` of `results/live/main/units/*.json`. For the frozen main result it checks the expected numbers and the number of units. For a full recalculation of the memory and the saved tables (it **modifies the files in `results/`**), see the [safe procedure in `RUNBOOK.md`](RUNBOOK.md#safe-recalculation-in-a-separate-working-copy). The integrity of the frozen sources and raw measurements is checked by `python3 scripts/check_frozen_artifacts.py` against the [SHA-256 manifest](frozen_artifacts.json): 6 groups, 659 files, without `timing/` and the derived tables.

**Status:** "main" — the original comparison on `eval`; "post hoc" — studies after the freeze. The pilot, the smoke test and `holdout` are not combined with the main score.

## Main comparison

<a id="e1"></a>
### E1. Memory level: 778/780 against 700/780

- **Data:** [`ours@cache.jsonl`](../results/memory_level/eval/ours@cache.jsonl), [`full_history.jsonl`](../results/memory_level/eval/full_history.jsonl), [`shared_rag_bm25.jsonl`](../results/memory_level/eval/shared_rag_bm25.jsonl); [tables](../results/memory_level/eval/tables.md).
- **How to check:** `python3 scripts/evidence_summary.py --verify`; for a new calculation — `make memory-level SPLIT=eval` (it overwrites the files).
- **Scope:** 210 `eval` scenarios, 780 checkpoints per system. **Status:** main, memory level.
- **Limit of the conclusion:** [`score_context`](../src/mam/scoring.py#L45) looks for the lines and attributes of the context, not for the agent's reasoning; the comparison is subject to the strict `absent` and `disputed` rules (section 5 of [`REPORT.md`](../REPORT.md#5-memory-level-results)).

<a id="e2"></a>
### E2. Live answers: 124/156 for `ours`

- **Data:** [210 saved units](../results/live/main/units/) and [summary tables](../results/live/main/tables.md); the analysis of all checkpoints — [section 6 of the report](../REPORT.md#6-live-layer-results).
- **How to check:** `python3 scripts/evidence_summary.py --verify` sums *all* `checkpoints` (124/156 `ours`, 119/156 `rolling_summary`, 117/156 BM25, 108/156 `full_history`, 104/156 window). `make live-tables DIR=results/live/main` rebuilds the summary, but the `Outcomes` table selects only part of the checks (C0/C6 all, C1–C5 factor ones).
- **Scope:** 21 scenarios × 2 repeats × 5 systems = 210 units, 156 checks per system. **Status:** main, live layer.
- **Limit of the conclusion:** two repeats of the same scenarios are not an independent large sample; the result does not prove a general superiority.

<a id="e3"></a>
### E3. The C1/C3 gap depends on the criterion

- **Data:** [strict count](../results/live/main/tables.md), [soft check of C1/C3](../results/post_hoc/c1c3_lenient.md), [analysis of the controls](../results/post_hoc/controls.md); [two units of one checkpoint](../results/live/main/units/full_history__C1-eval-0000__r0.json) and [repeat r1](../results/live/main/units/full_history__C1-eval-0000__r1.json).
- **How to check:** [`WALKTHROUGH.md`](WALKTHROUGH.md) analyzes `cpx-1` down to the `violations` field; additional control commands are given in [`RUNBOOK.md`](RUNBOOK.md#5-additional-checks-post-hoc).
- **Scope:** 6 strict live factor checks per category C1 and C3; the soft C1+C3 — 12 points. **Status:** main count + a separate *post hoc* check of the interpretation.
- **Limit of the conclusion:** a correct value with a mention of the old one is evaluated as a failure; the correctness of the actions and the usefulness of an explanation are not identical to such a count.

<a id="e4"></a>
### E4. C6: `ours` loses the result because of the Worker's actions

- **Data:** [C6 in the live-layer tables](../results/live/main/tables.md), [`ours` unit, C6-eval-0002](../results/live/main/units/ours__C6-eval-0002__r0.json) and [analysis of the causes](../REPORT.md#8-failure-analysis).
- **How to check:** in the `checkpoints` of the unit find `cp-1`, `cp-3` and the fields `label`, `reachable`; then verify the absence of a `write` for `e-0002`, `e-0086` in the [`ours` trace, r0](../results/live/main/traces/ours__C6-eval-0002__r0.jsonl). A step-by-step reproducible example is in the [failure analysis](FAILURE_WALKTHROUGH.md).
- **Scope:** three lengths of the C6 history × 2 repeats, 18 checks per system. **Status:** main.
- **Limit of the conclusion:** the label `agent` means that the fact did not reach memory under this protocol; the cause cannot be automatically attributed to the storage algorithm alone.

<a id="e5"></a>
### E5. Cost and number of calls

- **Data:** the fields `calls`, `cost_usd`, `totals` in the [units](../results/live/main/units/); [table Cost, tokens and time](../results/live/main/tables.md), [decision D21](DECISIONS.md#d21), [result D22](DECISIONS.md#d22).
- **How to check:** `make live-tables DIR=results/live/main` rebuilds the table from the saved units; the total accounting $6.275 + $3.415 = $9.69 is described in [section 6](../REPORT.md#6-live-layer-results).
- **Scope:** the main run of 210 units; the extraction is accounted for separately. **Status:** main.
- **Limit of the conclusion:** these are the prices returned by the CLI during the original run, **not** the current prices of the provider and **not** a guarantee of the cost of a repeat.

## Additional checks (*post hoc*)

<a id="e6"></a>
### E6. Presentation of the author and time changes the comparison

- **Data:** [blind classification](../results/post_hoc/presentation/blind.md), [matching](../results/post_hoc/presentation/classified.md), [control repeat](../results/post_hoc/control_repeat.md).
- **How to check:** the commands [`scripts/post_hoc_presentation.py`](../scripts/post_hoc_presentation.py) and [`scripts/post_hoc_control_repeat.py`](../scripts/post_hoc_control_repeat.py) are listed in the [RUNBOOK](RUNBOOK.md#5-additional-checks-post-hoc), or you can study the tables that are already saved.
- **Scope:** 48 additional presentation checks in C1/C3. **Status:** post hoc.
- **Limit of the conclusion:** the presentation comparison did not re-run `ours` under the same conditions; it is a check of the explanation of the gap, not a new independent main experiment.

<a id="e7"></a>
### E7. `ours3`: the improvement on the same `eval` was not repeated on new scenarios

- **Data:** [`ours3/criteria.md`](../results/post_hoc/ours3/criteria.md), [new scenarios and criteria](../results/post_hoc/fresh/criteria.md), [their tables](../results/post_hoc/fresh/tables.md).
- **How to check:** compare `ours3` 141/156 on the original scenarios with 70/78 for `ours3` and 71/78 for `ours` on the other 21 scenarios.
- **Scope:** 21 additional scenarios without overlap with variant A, one repeat; **not an independent dataset** (the same generator). **Status:** post hoc.
- **Limit of the conclusion:** the results of tuning cannot be presented as a confirmation of an advantage on new data.

<a id="e8"></a>
### E8. The evaluator misses rephrased constraints

- **Data:** [comparison of the original and the rephrasing](../results/post_hoc/paraphrase/comparison.md), [description of defect D39](DECISIONS.md#d39), [evaluation code](../src/mam/scoring.py).
- **How to check:** `python scripts/post_hoc_paraphrase.py compare` after setting up the environment from the RUNBOOK; the table shows the standard and the adjusted counts separately.
- **Scope:** three problematic constraint checks in the rephrased scenarios. **Status:** post hoc, a known defect of the evaluator.
- **Limit of the conclusion:** only the **calculation in the additional analysis** was corrected; the code of the frozen evaluator and the original numbers were not changed.

<a id="e9"></a>
### E9. `ours4`: the rules were fixed, but the criteria were not fully met

- **Data:** [`ours4/criteria.md`](../results/post_hoc/ours4/criteria.md), [D40](DECISIONS.md#d40), [D41](DECISIONS.md#d41).
- **How to check:** compare the 6/6 fixed constraints with 40 false records in 30 units and the verdict `partial`.
- **Scope:** 27 units of set A and 21 units of `ours4` on set B (different comparison tasks). **Status:** post hoc.
- **Limit of the conclusion:** on the adjusted live checks of the constraints `ours3` is not worse than `ours4`; false rules worsen the result by the criteria.

<a id="e10"></a>
### E10. Mem0 and Graphiti: comparison only on subsets

- **Data:** [Mem0, common set of 12](../results/post_hoc/external/mem0/common12.md), [Graphiti](../results/post_hoc/external/graphiti/tables.md), [D44](DECISIONS.md#d44).
- **How to check:** compare the columns on the same 12 scenarios; do not mix them with the full main run. The external scripts are [`external/run.py`](../external/run.py).
- **Scope:** Mem0 on limited subsets, Graphiti 12 units; A-Mem `NOT RUN`. **Status:** post hoc.
- **Limit of the conclusion:** the configurations and prices of the external tools are specific to this run; C4 was not checked for Graphiti.

## How to use this map

Each main result in [`RESULTS.md`](RESULTS.md) has a link to E1–E10. For the facts of the original study rely on the original files and the verifiable recalculation; for *post hoc* results state the status, the sample and the known deviations from the protocol. The technical and methodological limitations are collected in [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md), and the history of decision-making is in [`DECISION_INDEX.md`](DECISION_INDEX.md).
