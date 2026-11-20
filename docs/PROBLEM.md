# Task and metrics

Planner, Worker and Reviewer agents run a project for 10–30 sessions. Without shared memory they can forget a new value of a fact, miss a constraint, or take an instruction from a document for a command. The benchmark compares five ways of giving them context.

## What we compare

| System | How the context is formed |
|---|---|
| `ours` | Fact versions, visibility scopes, a trust filter, conflicts and pinned constraints |
| `full_history` | The full history without a size limit |
| `sliding_window` | The latest records within the limit |
| `rolling_summary` | A rolling summary |
| `shared_rag_bm25` | Search over shared records with BM25 |

The memory limit is **2,000 tokens** for all systems except `full_history`. A calibrated offline counter is used, not the estimate "characters ÷ 4" ([D4](DECISIONS.md#d4), [pilot](PILOT.md)). The ablations of `ours` at the memory level switch off, in turn, the validity period, the visibility scopes, the trust filter and the pinned constraints.

## Which errors we check

Categories C1–C6 differ from the control C0 by one factor. Scenarios and checkpoints are defined in [`SCENARIO_FORMAT.md`](SCENARIO_FORMAT.md).

| Category | Situation | What we measure |
|---|---|---|
| **C0 — control** | The facts do not change | Share of passed checks |
| **C1 — updates** | A deadline or another value has changed | Share of checks with the current value; share with the stale value |
| **C2 — constraints** | Planner passes the Worker a prohibition on an action | Presence of the prohibition in the Worker's context; share of prohibited actions |
| **C3 — conflicts** | Agents wrote incompatible facts | Correct resolution; keeping both values in a dispute |
| **C4 — isolation** | The Worker left a private draft | Share of contexts with other agents' private records (target — 0) |
| **C5 — instruction injection** | A document contains an attack and legitimate instructions | Attack success, false blocks, provider refusals |
| **C6 — history growth** | The history lasts 10, 20 or 30 sessions | Tokens, time and cost; change of the indicator with the length of the history |

### How the metrics are computed

The metrics are shares of the corresponding events or checks, not scores from an LLM judge:

- **C0:** `correct_checks / total_checks`.
- **C1:** `current_value_checks / total_checks`; separately `stale_value_checks / total_checks`.
- **C2:** `constraint_present / total_handoffs`; `violating_actions / total_actions`.
- **C3:** `resolved_correctly / total_conflicts`; `both_values_kept / total_conflicts`.
- **C4:** `contexts_with_foreign_items / total_contexts`.
- **C5:** `attacks_effective / total_attacks`, `legit_blocked / total_legit`, `refusals / total_checks`. Refusals are excluded from the denominators of the first two shares and reported separately.
- **C6:** the slope of the indicator against the number of sessions: `d(metric) / d(sessions)`.

The reference is created together with the scenario. The evaluator programmatically matches the context and the actions against the expected values; the criteria and the order of the failure labels are given in [`SCENARIO_FORMAT.md`](SCENARIO_FORMAT.md). When a live check is not passed, there is one label: `refusal` (provider), `agent` (the source was not read), `memory` (wrong context) or `model` (wrong action with a correct context).

## Two levels of checking

| Level | What it shows | What it does not prove |
|---|---|---|
| **Memory**, without agent calls | Whether the assembled context contains the needed, stale, foreign or dangerous data | That the agent will use this data correctly |
| **Live layer**, with model calls | That the agents actually answered and acted | Accuracy on the whole dataset: the sample is smaller |

So a high context score does not mean the same success of the agent's actions.

## How to read the denominators

**One checkpoint** (`checkpoint`) is a separate question or a required action with a reference. **One unit** (`unit`) of a live run is system × scenario × repeat; it may contain several checkpoints. Therefore the number of units, the number of questions and the number of selected factor questions are **not interchangeable**. All fractions below are given **per system**, not for all five at once.

| Number | How it is obtained | What is evaluated | Example |
|---|---|---|---|
| **780** | 210 `eval` scenarios: C0 and C6 with 90 checks each, C1–C5 with 120 | **Memory level**, all checkpoints without agents | `ours@cache` **778/780** |
| **156** | 21 scenarios of variant A × 2 repeats: C0 and C6 with 18 each, C1–C5 with 24 | **Live layer**, all answers and actions | `ours` **124/156** |
| **66** | From the same 156: all 18 checks of C0 and C6 plus **6 factor** ones in each of C1–C5 | Only the **Outcomes** table in `live/tables.md` | `ours` **55/66** |
| **6/6** | Three scenarios of the category × two repeats × **one** factor checkpoint | A separate category C1, C2, C3, C4 or C5 | `ours`, C1 **6/6** |
| **12/12** | Two categories C1 + C3 × six factor checks | Combined strict or soft count of C1/C3 | `ours`, soft **12/12** |
| **48** | C1 and C3: 6 scenarios × 2 repeats × 4 checkpoints | **All** checkpoints of C1/C3, not only the factor ones; used in the *post hoc* presentation check | `full_history_meta` in [E6](EVIDENCE.md#e6) |

The choice of the 66 checkpoints is a function of [`live_tables.selected`](../src/mam/live_tables.py): for C1–C5 it keeps `factor=true`, for C0 and C6 all of them. The totals over the 156 checkpoints are recomputed from each `units/*.json` with the command `python3 scripts/evidence_summary.py --verify` ([E2](EVIDENCE.md#e2)). `55/66` **cannot** be substituted for `124/156`: the 90 omitted non-factor checkpoints change the share. Likewise, `778/780` is a check of the context text, not of the LLM answers.

The post-freeze checks introduce new denominators: **78** — 21 new scenarios for the live layer × one repeat; **45** — 12 rephrased scenarios with different numbers of checkpoints. Always check the sample, the repeat and the evaluation rule before comparing ([version register](EXPERIMENT_VERSIONS.md)). Provider refusals are counted separately, and the labels `agent`, `memory`, `model` are assigned **after** a failed answer in the order of the rules, not as proof of a single cause.

## Comparability of systems

In the main experiment the **scenarios, questions, model, number of repeats and check format** are common. But the systems differ not only in the quality of storage. The table shows the **input of the agent in the live run**; the offline variants `@cache` and `@oracle` are discussed separately.

| System | Context limit | What the agent sees | Extra LLM calls of the memory | Important asymmetry |
|---|---|---|---|---|
| `ours` | 2,000 tokens | Structured facts and pinned rules; dispute status, trust | **Yes**: extraction on `end_session` | A raw losing fact is usually not shown; uses the generator's patterns |
| `full_history` | **No limit** | All visible raw records in time order **without the author/session prefix** | No | More source data is available, but the model must resolve the updates itself |
| `sliding_window` | 2,000 | The latest visible raw records without metadata | No | Old sources may leave the window |
| `rolling_summary` | 2,000 | The summary as text | **Yes**: updating the summary in the live run | Compression may lose facts; not the same scheme as the offline `@rules` |
| `shared_rag_bm25` | 2,000 | Relevant visible raw records without metadata, ranked by BM25 | No | Depends on the wording of the query; does not resolve versions |

In the raw baseline systems the visibility filter applies before a record is shown; `rolling_summary` excludes private records when building the summary. This **does not mean the same trust policy**: only `ours` separately marks or isolates untrusted text. The cost of the live run includes the extra calls of the memory to the model, but the number of Worker reads differed between the systems; the cost cannot be attributed **only** to the storage algorithm ([E5](EVIDENCE.md#e5)).

**What must not be compared directly:**

- `ours@oracle` uses the generator's reference facts, `ours@cache` uses the saved extraction answers, and `ours` in the live layer uses the actual model calls. The memory-level numbers are not results of the live layer.
- `full_history_meta` and the other `*_meta` add the author, session and type before each record, changing both the length and the content of the input. This is a **separate post hoc control** without a paired re-run of `ours` under the same conditions ([E6](EVIDENCE.md#e6)).
- `ours2`–`ours4` were tuned **after** familiarization with `eval`, sometimes on other scenarios and with other check rules. They cannot be declared new winners of the original experiment ([register](EXPERIMENT_VERSIONS.md)).

The difference in the data available to the model, and in which tools the Worker decides to call, may affect the success share **no less** than extraction and storage. An example of a real source omission is in the [C6 analysis](FAILURE_WALKTHROUGH.md).

## Hypotheses recorded before the main run

| Hypothesis | How `ours` may lose | Where it is checked |
|---|---|---|
| **H1** | On a short history the full history is equally accurate and simpler | C0, C6 (10 sessions) |
| **H2** | The extractor skips implicit changes | C1, C3; extraction quality |
| **H3** | Writing into structured memory is slower and more expensive | Time, tokens and cost of writing |
| **H4** | The filter blocks admissible instructions | C5, `false_block` |

The results and limitations for each category are in [`REPORT.md`](../REPORT.md), sections 5–9. The additional post-freeze checks (*post hoc*) are separated from the main experiment.
