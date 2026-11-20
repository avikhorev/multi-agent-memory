# Known defects and limitations

This lists **what may distort a run or its conclusions**, how to recognize it, and what to do now. The listing does not mean that the problem is already fixed: the main code and the saved results have not changed since the freeze. The history of the research and the rationale are in [`DECISIONS.md`](DECISIONS.md); the sources of the numbers are in [`EVIDENCE.md`](EVIDENCE.md).

**Notation:** "defect" — an observable error of the implementation or the evaluator; "limitation" — a property of the experimental protocol that narrows the scope of the conclusion; "not verified" — a missing measurement. The status "open" does not promise a fix date.

## Defects affecting the run or the evaluation

<a id="budget-resume"></a>
### 1. Cost limit on resumption — open

- **Where:** [`run.py`](../src/mam/run.py), [`extraction.py`](../src/mam/extraction.py), [D20](DECISIONS.md#d20).
- **Symptom:** after resumption `MAX_COST` may stop the work early: the old batches are counted in the sum of spending, while the average price is estimated only from the completed units of the current batch.
- **What to do:** track the total cost **in the saved results** after each batch; treat the limit as soft, not as a guaranteed budget protection. D20 describes a historical workaround by raising the projection limit, but it must not be applied without independent control of the spending.
- **Status:** a known defect, not fixed; previously completed units were not recalculated.

<a id="parallel-budget"></a>
### 2. Parallel expensive units may exceed the limit — open

- **Where:** [D44](DECISIONS.md#d44), [section 15 of the report](../REPORT.md#15-external-baseline-systems-mem0-and-graphiti-post-hoc).
- **Symptom:** before the first unit completes, the average price estimate is zero; the runner may launch all parallel tasks. Graphiti exceeded the limit of $2.5 per system: $2.58 was recorded, about $0.7 more was estimated but not saved.
- **What to do:** start expensive external runs with a small number of threads and a small sample; check the actual spending, not only `MAX_COST`. This is not proof of an overspend in the original main run.
- **Status:** a known limitation of the budget control, not fixed.

<a id="scorer-paraphrase"></a>
### 3. The evaluator misses some violations of prohibitions — open

- **Where:** [`scoring.py`](../src/mam/scoring.py), [D39](DECISIONS.md#d39), [comparison table](../results/post_hoc/paraphrase/comparison.md).
- **Symptom:** `update_record` on the same semantic attribute under a different name may pass the standard field check. With rephrased constraints `ours` made a forbidden edit in 3 of 3 cases, but the original evaluator did not record the violation.
- **What to do:** for the additional checks of the constraints look at the **adjusted count of D39** and the real actions, not only at `passed`. The main count has not been recalculated retroactively.
- **Status:** the evaluator defect is not fixed; the adjusted values are published separately (*post hoc*).

<a id="order-dependence"></a>
### 4. Version resolution depends on the write order — open

- **Where:** [`Ours._resolve`](../src/mam/systems/ours.py), [write order check](../results/post_hoc/write_order.md), [section 9 of the report](../REPORT.md#9-limitations).
- **Symptom:** with the reverse write order the outcome changes for **4 of 11** conflicting keys on the original `eval` (all four are C1). Facts without a date get relative time by the order of arrival; an earlier-written untrusted value may also outrank an older trusted one.
- **What to do:** do not treat the behavior as deterministic with respect to a permutation of the input records; test separately the records without dates and real concurrent updates.
- **Status:** confirmed by an additional offline check; concurrent writing was not tested.

## Limitations of the study

<a id="template-dependence"></a>
### 5. Extraction and the filter know the generator's templates

- **Where:** [`extract.py`](../src/mam/extract.py), [D25](DECISIONS.md#d25), [section 9 of the report](../REPORT.md#9-limitations).
- **Symptom:** the closed list of attributes, the scheme `Atlas/<module>` and the regular expressions for constraints and sources are matched to the scenario templates; real agent notes without `x-` do not get into `ours`.
- **How to read the result:** the completeness of the extraction on `eval` and `holdout` **does not measure** robustness to arbitrary text. Rephrasing was studied only on a small sample after the freeze.
- **Status:** a limitation of applicability, not fixed. The gaps and the plan for production work: [`PRODUCTION.md`](PRODUCTION.md).

<a id="agent-protocol"></a>
### 6. The agent's working cycle is too short for some tasks

- **Where:** [`live.py`](../src/mam/live.py), [session diagram](ARCHITECTURE.md#2-one-session), [E4](EVIDENCE.md#e4).
- **Symptom:** the Planner is called once, the Worker twice with the same context, the Reviewer once. The Worker chooses an action and sometimes updates a record **instead of** reading the proposed source; the Reviewer does not see new facts until the session ends.
- **How to read the result:** misses labeled `agent` must not be treated as a proven defect of the storage algorithm; [C6-eval-0002](FAILURE_WALKTHROUGH.md) shows a real trace with an unselected source. The behavior of a full multi-step agent cycle was not measured.
- **Status:** a limitation of the protocol.

<a id="strict-score"></a>
### 7. The strict count and the presentation of the baseline systems change the interpretation

- **Where:** [E3](EVIDENCE.md#e3), [E6](EVIDENCE.md#e6), [`scoring.py`](../src/mam/scoring.py).
- **Symptom:** a correctly named current value together with the old one counts as a failure; the original `full_history` does not show the author and time in the same form as the late control `full_history_meta`.
- **How to read the result:** separate the strict main count from the soft additional count and do not compare them as one metric. The explanation of part of the gap by presentation is a *post hoc* result, without a re-run of `ours` under the same conditions.
- **Status:** a limitation of the metric and of the comparison protocol.

<a id="security-scope"></a>
### 8. The checks of protection and isolation are limited to synthetic data

- **Where:** [`THREAT_MODEL.md`](THREAT_MODEL.md), [`ASSUMPTIONS.md`](ASSUMPTIONS.md), [section 9 of the report](../REPORT.md#9-limitations).
- **Symptom:** the filter of untrusted instructions looks for textual signs, not for the meaning of the threat; `holdout` contains no independent set of such attacks. The C4 check on the cache may fail to detect a leak simply because the extractor did not take the fact from the draft.
- **How to read the result:** 6/6 live checks of C4 and C5 for all systems **do not prove** robustness in an arbitrary environment.
- **Status:** a limitation of coverage.

<a id="trace-detail"></a>
### 9. The saved traces do not contain the full context

- **Where:** [`live.py`](../src/mam/live.py), [traces of the main run](../results/live/main/traces/), [end-to-end example](WALKTHROUGH.md).
- **Symptom:** the trace contains the IDs of the items and shortened answers, but not the full text of each prompt and of the memory.
- **What to do:** compare the trace with `units/*.json`, with the scenario itself and with the context assembly code. Do not present a reconstructed string as the exact saved prompt.
- **Status:** a limitation of observability.

<a id="external-scope"></a>
### 10. External systems and part of the runs are not fully verified

- **Where:** [E10](EVIDENCE.md#e10), [D44](DECISIONS.md#d44), [`RUNBOOK.md`](RUNBOOK.md).
- **Symptom:** Graphiti was checked on 12 units and without C4; A-Mem — `NOT RUN`; a full live run in Docker and the API-key authorization path were not verified. The spending of one stopped Graphiti run is estimated but not confirmed by saved units.
- **How to read the result:** do not transfer the conclusion about the absence of a leak or the comparative cost to unverified configurations.
- **Status:** not verified / partly verified.

## How to report a new problem

State the scenario ID, the system and the repeat, the path to the `unit` and the `trace`, the expected and the actual behavior, the class of the problem (code / evaluation / protocol) and the moment of discovery relative to the freeze. Do not correct the old numerical conclusions without a separate record of the change of criteria. The history of decisions is kept in [`DECISIONS.md`](DECISIONS.md).
