# mam

## Overview

The `mam` package ("Memory for a multi-agent system and a benchmark to evaluate it", `__init__.py`; `pyproject.toml` declares no runtime dependencies and Python 3.11 or newer). It has four parts:

- **Scenarios**: types, a seeded generator, a validator of the ground truth and a tool simulator.
- **Memory**: shared types, an offline token counter, fact extractors, a quarantine guard and the memory systems in [`systems`](./systems/README.md).
- **Scoring**: programmatic checks of the context a memory builds and of the answer and actions of an agent.
- **Runners**: a memory-level evaluation without a model, a live layer in which model agents play a scenario, an extraction pass that saves model answers for replay, and table printers.

Modules are run as `python -m mam.<module>`.

## Interface

Types and utilities

- `types.py`: frozen dataclasses `Fact`, `Entry`, `Reader`, `ContextItem` and the mutable `Context` (with `render()`).
- `tokens.py`: `count(text)`, a deterministic regex-based token estimate with no network.
- `guard.py`: `fragments(text)`, `split_untrusted(text) -> (kept, held)`; holds back lines that address an agent or AI, tell it to ignore rules, or set behaviour for future sessions.
- `selection.py`: `select_live(manifest_path, size)` with `size` one of `smoke`, `B`, `A` (`PER_CATEGORY`).

Scenarios

- `scenario.py`: `Scenario`, `Session`, `Event`, `Constraint`, `Checkpoint` and its parts, `ActionPattern`; `dumps`, `loads`, `dump`, `load`, `to_dict`, `from_dict`.
- `generate.py`: `generate(category, seed, ...)`, `build_base`, `FactorContext`, `factor_c1` to `factor_c6` (plus `factor_c4_legacy` and `factor_c5_legacy` used by the holdout split), `control_of`, `strip_factor`, `regenerate`, `split_specs`, `generate_split`, `write_split`, `HOLDOUT`, `DEV_COUNTS`. Entry point: `python -m mam.generate --split {dev,eval,holdout} --out DIR`.
- `validate.py`: `validate(scenario, check_determinism=True) -> list[str]`, with error strings that start with a rule id (`R1` to `R7`); also `resolve`, `known_facts`, `current_facts`, `private_only_ids`.
- `simulate.py`: `Simulator` (`call(tool, args)`, `action_log`) and `entries(scenario) -> list[Entry]`.

Extraction

- `extract.py`: `Extraction`, `OracleExtractor`, `RulesExtractor`, `CacheExtractor`, `LLMExtractor`, `make_extractor(kind, cache_path, llm)`, `rule_constraints`, `rule_facts`, `UNKNOWN_TIME`, `DAY_ZERO`.
- `extraction.py`: `extract_scenario`, `run_pass`, `merge_rows`, `select_ids`, `Pass`. Entry point: `python -m mam.extraction run|merge`.
- `extraction_quality.py`: `quality(cache_path, data_dir)`, `render`. Entry point: `python -m mam.extraction_quality CACHE DATA_DIR`.

Model access and agents

- `llm.py`: `LLMClient` protocol, `ClaudeCliClient`, `FakeClient`, `LLMResult`, `Usage`, `MODEL`, `PINNED_CLI_VERSION`, `ENV_WHITELIST`, exceptions `LLMError`, `InfrastructureError`, `RateLimitTimeout`.
- `preflight.py`: `check_access`, `main`, `EXIT_NO_ACCESS = 78`. Entry point: `python -m mam.preflight`.
- `agents.py`: `run_agent(llm, role, ...) -> AgentResult` for the roles `planner`, `worker`, `reviewer` (`SYSTEMS`); `parse_action`, `build_prompt`, `ActionError`.

Evaluation

- `scoring.py`: `normalize`, `score_context`, `score_action`, `label_failure` (labels `ok`, `agent`, `memory`, `model`, `refusal`), `CheckResult`.
- `memory_eval.py`: `run_scenario`, `make_system`, `systems_for`, `DEFAULT_SYSTEMS`, `ABLATIONS`. Entry point: `python -m mam.memory_eval --split ... --out DIR`.
- `live.py`: `run_live(scenario, cfg, llm, *, repeat, limit)`, `session_source`, `reachable`.
- `run.py`: `plan_units`, `run_units`, `trace_lines`, `Unit`, `Report`. Entry points: `python -m mam.run live ...` and `python -m mam.run trace SCENARIO --dir DIR`.
- `tables.py`: `load_results`, `render`, `interval`. Entry point: `python -m mam.tables RESULTS_DIR [--title T]`.
- `live_tables.py`: `load_units`, `summarize`, `paired_counts`, `render`. Entry point: `python -m mam.live_tables RESULTS_DIR`.

Other public names (not covered above): `scoring.checkpoint_of`, `scoring.MONTHS`; `memory_eval.scenario_paths` and the flags `--data`, `--systems`, `--limit`, `--cache` of `memory_eval.main`; `generate.ATTRS`, `FACTORS`, `LEGACY_FACTORS`, `RESOLUTION_CYCLE`, `hard_options`; `validate.AUTHORITY` (duplicates `systems.ours.AUTHORITY`); `tables.per_scenario`, `METRICS`, `BOOTSTRAP`, `SEED`; `live_tables.category`, `selected`, `n_sessions`, `slope`, `pct`, `LABELS`; `extract.sentences`, `LABELS`, `ATTRIBUTES`; `agents.TOOLS`, `FORMAT`, `SAFETY`; `llm.default_runner`; `selection.FIRST_TEN`; `preflight.NO_ACCESS`, `NO_CLI`. `generate.DAY0` duplicates `extract.DAY_ZERO`.

Subpackage

- [`systems`](./systems/README.md): the memory systems and the factory `mam.systems.create`.

## Invariants

- Generation is deterministic: the base world and the factor of a category use separate random streams, so `strip_factor(s)` equals `control_of(s)`; `validate` rule `R7` fails when `regenerate(s)` differs from `s` (`generate.py` module docstring, `validate.py:validate`).
- Factor events and checkpoints carry `factor=True` (`Fact` has no `factor` field) and ids from a separate namespace: events `x-NNNN`, facts `fx-NNNN`, checkpoints `cpx-N`; the C2 constraint uses id `k-0001` (`generate.py:FactorContext`). The holdout split keeps the legacy C4 and C5 builders so it stays reproducible byte for byte (`generate.py:LEGACY_FACTORS`).
- Memory-level evaluation calls no model and is deterministic; only the timing files vary (`memory_eval.py` docstring).
- Every model call is stateless: one user message, a new process, closed stdin, an empty temporary working directory and the environment filtered by `ENV_WHITELIST` plus `DISABLE_AUTOUPDATER=1` (`llm.py:ClaudeCliClient.complete`, `_env`). `run.py` records `api_key_set` (from `ANTHROPIC_API_KEY`) in every unit manifest. The `claude` CLI version must equal `PINNED_CLI_VERSION` when `check_version=True`.
- An agent replies with one strict JSON object with keys `tool`, `args`, `answer`, `notes`; `parse_action` also rejects unknown `tool` values (`TOOLS`) and truncates `notes` to three. `run_agent` makes at most two attempts in total, a budget shared by refusals and invalid JSON (the retry prompt differs by cause) (`agents.py:parse_action`, `run_agent`).
- A model-provided event date is accepted only if the message itself contains it; otherwise the fact gets `UNKNOWN_TIME` (`extract.py:_stated`).
- A finished unit or scenario file is never recomputed: runners skip existing outputs and stop at the time or cost limit (`run.py:run_units`, `extraction.py:run_pass`). The cost cap is a projection (`cost + average cost * pending >= max`) checked before each unit is submitted, so units already running can overshoot it; with no finished unit the average is 0.
- The live layer builds `ours` and `rolling_summary` with `extractor="llm"` and the benchmark client; it never uses the oracle or rules extractors (`live.py:run_live`). `run_live` returns a dict with keys `checkpoints`, `calls`, `memory`, `totals`, `trace`, `actions`.
- `python -m mam.run live --split` accepts `dev` and `eval` only; `memory_eval` and `extraction` also accept `holdout`.
- Exit codes of the runners: `0` ok, `2` incomplete or failed units, `75` rate-limited (`run.py:EXIT_*`, `extraction.py:EXIT_*`); `preflight` uses `78` for no access.
- In a live run the harness writes user messages, factor notes and drafts, and tool data the Worker actually reads, plus the `notes` the agents return; ordinary scripted notes are not written (`live.py` module docstring, `run_live`, `reachable`).

## Side Effects

- Subprocess: `ClaudeCliClient` runs `claude -p ...` (model `MODEL`) and `claude --version` (`llm.py`); it sleeps with growing delays on rate limits and records them in `infra_log`. `preflight.main` makes one test call.
- Filesystem writes:
  - `generate.write_split` writes one JSON per scenario and `manifest.json` (with sha256 per scenario) into `--out`.
  - `memory_eval.main` writes `<out>/<system>.jsonl` and `<out>/timing/<system>.jsonl`.
  - `extraction.run_pass` writes `<out>/scenarios/<id>.jsonl`, `<id>.meta.json` atomically (temporary file and `os.replace`) and appends to `failures.log`; `merge_rows` writes the merged cache file.
  - `run.run_units` writes `<out>/units/*.json` and `<out>/traces/*.jsonl` atomically, appends to `failures.log` and `infra.log.jsonl`.
- `run._commit` runs `git rev-parse HEAD` unless `MAM_COMMIT` is set (the `run.py` docstring says "There are no repository operations here", which is out of date).
- Reads: scenario and manifest JSON under `data/<split>` or `holdout`, cache files, and result directories (`tables`, `live_tables`, `extraction_quality`, which only print to stdout).
- Cost: live and extraction runs spend model budget, bounded by `--max-cost-usd` (default 10.0) and `--max-minutes`.

## Verification

- Run: `make test` (`.venv/bin/python -m pytest`, tests under `tests/unit` and `tests/acceptance`)
- Run: `make test-generator` (`pytest tests/acceptance -m "not memory"`: all acceptance tests except the modules marked `memory`, `test_memory_properties.py` and `test_tokens.py`, so it also covers scoring, simulate, scenario I/O, labels, dataset and holdout tests; the `memory` marker description in `pyproject.toml` still says "modules not written yet")
