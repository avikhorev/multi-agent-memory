# Assumptions and limits of the experiment

These conditions are needed to interpret the numbers in [`REPORT.md`](../REPORT.md). They describe the **implemented** benchmark, not an arbitrary multi-agent system.

## Sessions and agents

- **Writing is sequential.** `clock` increases with each write. Conflict C3 consists of two incompatible records with different event times, not a race of parallel writers. During resolution, [`event_time`](../src/mam/generate.py#L320) is compared, which may differ from `clock`.
- **Events are set in advance.** The scenario does not change because of the agents' actions; therefore the reference is known by construction.
- **Four LLM calls per session:** the Planner — one, the Worker — two, the Reviewer — one. The agents have no independent loop or built-in tools (`--tools ""`). Actions are passed as text JSON; the tool is invoked by the wrapper [`run_live`](../src/mam/live.py#L57).
- **The Worker reads memory once per session.** Its second call receives the previous context and the tool result; it may choose one more `update_record`, but does not see the answer to this second action. The Reviewer accepts or rejects the result without a retry.
- **There are three tools:** `read_document`, `read_status`, `update_record`. The last one records an action for evaluation but does not change the world of the scenario.
- **Notes are passed to memory.** Every agent answer contains `notes`. `ours` performs extraction at `end_session`, not inside the session. Because of the filter by the `x-` prefix, ordinary notes of the live agents do not turn into facts; this is a limitation of the original implementation (D25 in [`DECISIONS.md`](DECISIONS.md)).
- **The calls are independent.** Between them only what got into the memory system is kept. This protocol makes the comparison of systems identical, but limits the transferability of the results to autonomous agents with several actions.

## Data and samples

- The scenarios are synthetic: a software rollout for a client; the scenario texts are in English. C0–C5 last 10 sessions, C6 — 10, 20 or 30.
- Each scenario has 2–4 checkpoints. The checks of one scenario are related; they cannot be counted as independent observations.
- In the live variant A, categories C1 and C3 contain two scenarios with an implicit change and one with an explicit one; in variant B — one of each kind. Each C5 contains an attack and a legitimate instruction.
- `dev` was used for debugging; the main numbers are taken from `eval`. `holdout/` contains hard scenarios, but it is built on the same class of templates and does not serve as an independent check of all properties ([limitations of the report](../REPORT.md)).

## Memory and model calls

- **The total memory budget is 2,000 tokens**, without the system prompt. `full_history` is not limited. The offline counter is calibrated against `usage`: the maximum error on the pilot's verification texts is 6.3%. The estimate "characters ÷ 4" is not used (D4 in [`DECISIONS.md`](DECISIONS.md)).
- All roles and the extraction use `claude-haiku-5-5`; the temperature is not set, `--effort low` is used. Turning off the thinking tokens did not succeed. The answer is a compact JSON ([format](SCENARIO_FORMAT.md)).
- A provider refusal (`refusal`) is retried once and then counted separately, not as a successful attack or defense. During extraction the refusal is stored in the cache and is not mixed with an ordinary skipped fact.
- At the memory level the LLM is not called. Extraction there works from the reference (`oracle`), from rules (`rules`) or from saved model answers (`cache`); the variant is indicated in the tables. The reference is not given to the baseline systems in the main comparison.

## How the result is measured

- The evaluation is programmatic, without an LLM judge. The context and/or actions are checked against the reference.
- The cost is taken from the CLI; input, output and cache tokens are stored separately. The tables contain the cost and the tokens without taking the cache into account.
- The memory level shows bootstrap intervals over the scenarios. In the live layer the sample is small: proportions, the spread across repeats and the paired differences are reported; confidence intervals are not built.

## What remains outside the main conclusions

Concurrent writing, other models and providers were not tested, nor RAG with embeddings (BM25 was used). The external Mem0 and Graphiti were compared **only after the benchmark was frozen**; A-Mem was not run (section 15 of [`REPORT.md`](../REPORT.md)). The live results refer to the limited agent loop described above.
