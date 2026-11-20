# Documentation

Start with [`README.md`](../README.md) to run the project. This folder describes the benchmark and how the memory works. To start the analysis, read the [short results overview](RESULTS.md); the evidence and traces are discussed in [`REPORT.md`](../REPORT.md). For a first look at how the memory works, see [an example of a successful update](WALKTHROUGH.md) and [an analysis of a real failure](FAILURE_WALKTHROUGH.md).

## What to read

| If you need to… | Document | Contents |
|---|---|---|
| **See how the system works** | [Visual demo](demo/README.md) | Four stages: source → memory → agent → evaluation; comparison of `ours` and `full_history` on C1/C6 |
| Run the tests or repeat the experiment | [Run guide](RUNBOOK.md) | Commands, model access, result directories, deviations when reproducing |
| Understand the task | [Problem statement](PROBLEM.md) | Categories C0–C6, result denominators, comparability and hypotheses |
| See a successful update | [End-to-end example](WALKTHROUGH.md) | A real C1, the fact version, the agent's answer and the strict count |
| Analyze an agent failure | [C6 analysis](FAILURE_WALKTHROUGH.md) | Missed source, trace, the `agent` label and its limitations |
| Understand the code | [Architecture](ARCHITECTURE.md) | Session cycle, reading and writing memory, conflicts, diagrams |
| Understand what production work requires | [Production](PRODUCTION.md) | Target design, gaps in the code and a check before deployment (a plan, not implemented) |
| Connect your own system | [Extension](EXTENDING.md) | Minimal implementation, registration, tests, running without an LLM |
| Check the numerical claims | [Evidence map](EVIDENCE.md) | Numbers, source JSON/JSONL, recalculation commands, samples |
| See the known defects and workarounds | [Problems and limits](KNOWN_ISSUES.md) | Open defects, metric limitations, what is not verified |
| Compare results with limitations | [Results overview](RESULTS.md) | The main experiment and additional checks on one page |
| Learn the exact benchmark rules | [Scenario format](SCENARIO_FORMAT.md) | JSON, reference, evaluator, interface [`MemorySystem`](../src/mam/systems/base.py#L21), tests |
| Understand the limits of the results | [Assumptions](ASSUMPTIONS.md) | Simplifications, limits of the protocol and measurements |
| Check memory safety | [Threat model](THREAT_MODEL.md) | Trust levels, visibility scopes, quarantine, false blocks |
| Look at the raw measurements | [Pilot](PILOT.md) | Claude CLI, tokens, time and preliminary cost |
| Tell apart `ours`, `ours@cache` and `ours2`–`ours4` | [Version register](EXPERIMENT_VERSIONS.md) | Code, samples and status of each comparison |
| Quickly find the current decision | [Decision index](DECISION_INDEX.md) | Status of D1–D45, including replaced and open items |
| Find the reason for a change | [Decision log](DECISIONS.md) | D1–D45: decisions, observations and checks in chronological order |

## Documentation support

`make docs-check` works without an LLM: it checks local links and anchors, commit-pinned links to lines of code, mentioned `make` targets, frozen numerical totals and the [SHA-256 of the source artifacts](frozen_artifacts.json). The same command runs in CI. For a **recalculation**, which overwrites `results/`, use a [separate working copy](RUNBOOK.md#safe-recalculation-in-a-separate-working-copy).

**Checklist for changes:**

- If [`score_action`](../src/mam/scoring.py#L95), [`score_context`](../src/mam/scoring.py#L45) or the choice of checkpoints changed — update the [metric definitions](PROBLEM.md#how-to-read-the-denominators), the [specification](SCENARIO_FORMAT.md) and check the numbers in [EVIDENCE](EVIDENCE.md).
- If a scenario or the generator changed — check `data/*/manifest.json`, update the description of the splits and **do not** silently overwrite the old reference answers.
- If a memory variant was added — update the [version register](EXPERIMENT_VERSIONS.md), check comparability and the *post hoc* status.
- If the raw measurements changed — record the reason and the source files **before** replacing the hashes in [`frozen_artifacts.json`](frozen_artifacts.json); do not present new results as the previous frozen run.

## How the evidence is organized

- **Before the freeze:** design, pilot, `dev` and the basic rules. The tag `benchmark-frozen` fixes the setup of the main experiments.
- **Main results:** `eval`, a separate `holdout` and the live run of variant A; see sections 5–9 of the report.
- **After the freeze (*post hoc*):** additional checks of presentation, new memory versions, new data and external systems; sections 11–15 of the report. Their results are useful but are not a pre-planned test of the main hypothesis.

The files `results/**/tables.md` and `results/post_hoc/` contain the tables and reports of individual runs. These are **measurement results**, not instructions for using the project. The commands for working with them are in the [run guide](RUNBOOK.md).

## Terms

| Term | Meaning |
|---|---|
| Scenario | A chain of sessions with set events and a reference |
| Checkpoint | A question or action for which the expected behavior is known |
| `ours` | The original structured memory used in the main comparison |
| `ours2`–`ours4` | Experimental variants created after the freeze |
| Memory level | A check of the assembled context without agent calls |
| Live layer | A check of agent behavior with model calls |
| `refusal` | A refusal by the provider; counted separately from memory and agent errors |
