# Results: summary

**Conclusion:** the structured memory `ours` passes the programmatic checks of the context better than the simple systems, especially on fact updates and conflicts. But **a general superiority in the actions of agents is not shown**: part of the gap is created by a strict evaluation rule, and `ours` makes the Worker read the source less often. All data and caveats are in [`REPORT.md`](../REPORT.md). **Where to check each number:** [evidence map](EVIDENCE.md); [limitations and defects](KNOWN_ISSUES.md).

**How to read the numbers:** `778/780` — checks of **context without agents**; `124/156` — **all** live checkpoints; `55/66` — only the checkpoints selected for the `Outcomes` table. [Where the denominators come from](PROBLEM.md#how-to-read-the-denominators) · [How the systems differ](PROBLEM.md#comparability-of-systems).

On one particular run, the causes of two opposite outcomes are shown in the [interactive walkthrough of the traces](demo/README.md). It illustrates the mechanism and **does not replace** the results on the whole sample.

## Main experiment

| What was checked | Result | How to read it |
|---|---|---|
| **[Context, `eval` (E1)](EVIDENCE.md#e1)** (210 scenarios, 780 checks) | `ours@cache` 778/780; `full_history` and BM25 700/780; summary 697/780; window 660/780 | The literal evaluator checks the text of the context; it does not measure whether the agent can compute the value |
| **[Live layer (E2)](EVIDENCE.md#e2)** (21 scenarios × 5 systems × 2 repeats, 0 failures) | `ours` 124/156 of all checks; summary 119/156; BM25 117/156; full history 108/156; window 104/156 | A small sample, not statistical proof of an advantage |
| **[C1/C3: updates and conflicts (E3)](EVIDENCE.md#e3)** | Strict count: `ours` 6/6 per category, most baselines 0/6; soft count on C1+C3: `ours` 12/12, baselines 8–11/12 | The ban on mentioning a stale value makes the strict gap much larger |
| **[C2/C4/C5: limits, isolation, attacks (E2)](EVIDENCE.md#e2)** | All systems 6/6 on the factor live checks in each category | An improvement in behavior from the filter and visibility scopes was not measured |
| **[C0/C6: short and long history (E4)](EVIDENCE.md#e4)** | `ours` is not better than the baselines; on C6 `ours` 12/18, BM25 14/18 | Losing the source at the Worker matters more than the quality of the facts already written |

The accounted cost of the main live run from the CLI answers is **$6.275**; with extraction it is **$9.69**. Recording in `ours` requires extra model calls, although the total cost per unit is lower ($0.0237 against $0.0329 for `full_history`): `ours` reads the sources less often. Details — sections 5–8 of the report and [cost sources (E5)](EVIDENCE.md#e5).

## Post-freeze checks (*post hoc*)

They should not be considered an independent confirmation of the result of the original `ours`: they use additional settings, criteria or data. The [register of variants and samples](EXPERIMENT_VERSIONS.md) helps to tell the name of an implementation from the name of a run.

| Check | Outcome |
|---|---|
| [Control repeat and author/time presentation (E6)](EVIDENCE.md#e6) | The overall order of the systems is close to the main one, but part of the C1/C3 advantage is explained by the format of the raw history: the gap between `ours` and `full_history` on 48 checks dropped from 14 to 4 |
| [`ours3` on the original scenarios (E7)](EVIDENCE.md#e7) | 141/156 against 124/156 for `ours`, but this is a third setting on the same `eval` |
| [New scenarios for the live layer (E7)](EVIDENCE.md#e7) | `ours3` 70/78, `ours` 71/78, BM25 62/78: the advantage of `ours3` over `ours` was not confirmed |
| [Rephrased prohibitions (E8)](EVIDENCE.md#e8) | `ours` violated 3 of 3, but the standard evaluator did not notice: an adjusted count is required (D39) |
| [`ours4`: fixing constraints through the model (E9)](EVIDENCE.md#e9) | Fixing 6/6; a gain in live checks relative to `ours3` is not shown; there are false rules |
| [Mem0 and Graphiti (E10)](EVIDENCE.md#e10) | On comparable subsets the result is close to BM25: Mem0 37/48 against 37/48; Graphiti 17/24 against 16/24. A-Mem was not run |

Details: sections 11–15 of [`REPORT.md`](../REPORT.md); decisions and changes of criteria — [`DECISIONS.md`](DECISIONS.md).

## Main limitations

Details, reproducible cases and workarounds are in [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md).

- The `ours` extractor and filter know part of the generator's patterns, and `holdout` is not fully independent.
- A strict comparison with the reference does not always reflect a useful answer; the constraint evaluator misses field renames.
- Agents issue only four model calls per session. The Worker may not read the source ([analysis of a real C6](FAILURE_WALKTHROUGH.md)), and the Reviewer often checks the context before facts are extracted.
- Conflict resolution may depend on the order of writes; protection against prompt injection is based on signs in the text.

These are limitations of the results, not a claim that all the listed errors occur in ordinary work tasks.
