# Memory variants and experiment versions

This reference answers the question: **which exact code, on which scenarios and with which settings produced the published number?** It complements the [decision history D1–D44](DECISION_INDEX.md) but does not replace it.

## Main run (before the freeze of the results)

| Name in the data | Implementation | Mode and source of facts | Where the result is |
|---|---|---|---|
| `ours` | [`src/mam/systems/ours.py`](../src/mam/systems/ours.py) | Live `eval`, `extractor="llm"`; 21 scenarios of A × 2 repeats | [`main/units/`](../results/live/main/units/), [124/156 (E2)](EVIDENCE.md#e2) |
| `full_history`, `sliding_window`, `rolling_summary`, `shared_rag_bm25` | [`src/mam/systems/`](../src/mam/systems/) | The same 21 scenarios and repeats; `rolling_summary` is updated by the model | [Main tables](../results/live/main/tables.md) |
| `ours@cache` | `Ours`, [`memory_eval.py`](../src/mam/memory_eval.py) | Without the agent, 210 `eval` scenarios; saved extraction | [778/780 (E1)](EVIDENCE.md#e1) |
| `ours@oracle`, `ours@rules` | The same `Ours` | Without the agent; the generator's reference facts / extraction by rules | [`memory_level/eval/`](../results/memory_level/eval/) |
| `rolling_summary@cache`, `rolling_summary@rules` | [`summary.py`](../src/mam/systems/summary.py) | Without the agent; model cache / rules | [`memory_level/eval/`](../results/memory_level/eval/) |

The suffix `@cache` is **the extraction mode at the memory level**, not a new version of `ours` and not a repeat of the live run. The suffixes `-no_validity`, `-no_scopes`, `-no_trust`, `-no_pinned_constraints` switch off one mechanism of `ours` each in the ablations. `@oracle` uses the generator's knowledge, which the live agent does not have. These modes **must not** be combined into one common effectiveness total.

## Changes after the freeze (*post hoc*)

| Variant | Difference | Sample / status | Where to look |
|---|---|---|---|
| `full_history_meta` and other `*_meta` | A prefix `[session, author, kind]` is added to the raw text; the prefix counts toward the limit and the ranking | A separate C1/C3 check on 48 checkpoints; `ours` was **not** re-run under these conditions | [`post_hoc/presentation/`](../results/post_hoc/presentation/), [E6](EVIDENCE.md#e6) |
| `ours2` | A buffer of the unfinished session, BM25 filling, an additional treatment of disputes | The same 21 scenarios of A × 2; **134/156**; tuned on `eval` | [`scripts/post_hoc_ours2.py`](../scripts/post_hoc_ours2.py), [`criteria.md`](../results/post_hoc/ours2/criteria.md) |
| `ours2_lite` | `ours2` without the filling | The same sample, **121/156** | [`criteria_lite.md`](../results/post_hoc/ours2/criteria_lite.md) |
| `ours3` | `ours2` with the losing values blacked out in the filling and a filling limit of 300 tokens | The same 21 scenarios × 2, **141/156**; a third tuning on `eval` | [`scripts/post_hoc_ours2.py`](../scripts/post_hoc_ours2.py), [`criteria.md`](../results/post_hoc/ours3/criteria.md), [E7](EVIDENCE.md#e7) |
| `ours3` on new scenarios for the live layer | The same code without a further edit, but a different sample | 21 scenarios, 1 repeat; **70/78** against **71/78** for the original `ours`; not a fully independent sample | [`post_hoc/fresh/tables.md`](../results/post_hoc/fresh/tables.md), [E7](EVIDENCE.md#e7) |
| `ours4` | `ours3` with fixing of the constraints extracted by the model | Set A: 27 units on rephrased scenarios; B: 21 units; **no** common result on the original full A | [`scripts/post_hoc_ours4.py`](../scripts/post_hoc_ours4.py), [`criteria.md`](../results/post_hoc/ours4/criteria.md), [E9](EVIDENCE.md#e9) |
| Mem0, Graphiti | External adapters, their own environments and limitations | Only the matching subsets; A-Mem was **not run** | [`external/`](../external/), [E10](EVIDENCE.md#e10) |

**Do not confuse:** the original `ours` and the last experimental `ours4`; the change of the metric D39 and a change of the system; the experiment A of the main run and the sets A/B of the later scripts. The designations A/B are used locally in different checks.

## How to add a new row safely

1. Record the **name in the JSON manifest**, the implementation/commit, the extraction mode, the scenarios, the number of repeats, the model and the evaluation rules.
2. State what the number means: `all checks`, `factor only` or `context without the agent`; attach the numerator and the denominator.
3. Mark the status "main", "post hoc" or "not run". A new run **does not change** the status of the historical results.
4. Refer to the source `units/`, `*.jsonl` or a separate `criteria.md`, and extend the [evidence map](EVIDENCE.md) if the result has entered the overview.

For a new implementation of the memory interface see the [extension guide](EXTENDING.md). For the comparability of results — the [conditions matrix](PROBLEM.md#comparability-of-systems).
