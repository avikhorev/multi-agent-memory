# scripts

## Overview

Stand-alone command-line tools that sit beside the `mam` package in `src/`. They fall into two groups:

- **Repository checks** (stdlib only, offline, no model): verify the documentation, the frozen inputs and results, the frozen evidence totals and the generated browser demo.
- **Post-hoc analyses and variants** (`post_hoc_*.py`): analyses run after the results were frozen. Most read saved results from `results/` and write Markdown under `results/post_hoc/`. A few subcommands call a model through `mam.llm.ClaudeCliClient` and spend money; they are marked "paid" below. None of them edits `src/mam`; `post_hoc_c1c3.py` ("changes nothing"), `post_hoc_controls.py`, `post_hoc_presentation.py`, `post_hoc_ours2.py` and `post_hoc_ours4.py` say so in their docstrings, the others do not.

## Interface

### Repository checks

| Script | Entry point and flags | Reads | Writes |
|---|---|---|---|
| [check_docs.py](./check_docs.py) | `main()`, `--root` | `*.md` in the repo root and `docs/**/*.md` (`markdown_files`), `Makefile` (`make_targets`), `git show <ref>:<path>` for pinned links (`check_pinned`) | nothing |
| [check_frozen_artifacts.py](./check_frozen_artifacts.py) | `main()`, `--root`, `--manifest`, `--print-current` | `docs/frozen_artifacts.json` (`MANIFEST`) and the files matched by its globs (`group_digest`, `validate`) | stdout only |
| [evidence_summary.py](./evidence_summary.py) | `main()`, `--verify` | `results/memory_level/eval/<system>.jsonl` (`memory_counts`), `results/live/main/units/<system>__*__r*.json` (`live_counts`) | stdout only |
| [build_visual_demo.py](./build_visual_demo.py) | `main()`, `build_bundle()`, `render_js()`, `--check` | `data/eval/<scenario>.json`, `results/live/main/traces/*.jsonl`, `results/live/main/units/*.json` | `docs/demo/data.js` (`DEST`), only without `--check` |

### Post-hoc scripts

All of them put `src` on `sys.path` or rely on it being importable (see Invariants). Subcommands marked "paid" call a model and accept `--max-cost-usd`. The ones that go through `run_units` also stop at `--max-minutes` where the script defines that flag (`post_hoc_fresh.py`, `post_hoc_ours2.py`, `post_hoc_presentation.py`). Defaults differ per script: `--max-cost-usd` is 4.0 (`post_hoc_fresh.py`), 1.5 (`post_hoc_presentation.py`, `post_hoc_ours2.py`), 1.4 (`post_hoc_paraphrase.py`, every subcommand, although its docstring says 0.6 for `paraphrase`) and 1.0 (`post_hoc_ours4.py`); `--max-minutes` is 25 and `--workers` is 8 (`post_hoc_presentation.py` has only `--workers`; `post_hoc_paraphrase.py` has no `--max-minutes`).

| Script | Subcommands | Output |
|---|---|---|
| [post_hoc_c1c3.py](./post_hoc_c1c3.py) | `lenient`, `blind`, `join` | `results/post_hoc/c1c3_lenient.md`, `c1c3_blind.md`, `c1c3_classified.md`; hand labels in `results/post_hoc/c1c3_labels.json` |
| [post_hoc_controls.py](./post_hoc_controls.py) | none (runs `agent_behaviour`, `decomposition`, `cost`, `totals`, `growth`, `h2`) | `results/post_hoc/controls.md` |
| [post_hoc_control_repeat.py](./post_hoc_control_repeat.py) | `--main`, `--control`, `--out` | `results/post_hoc/control_repeat.md` (compares `results/live/main` with `results/live/control`, repeat 0 only) |
| [post_hoc_write_order.py](./post_hoc_write_order.py) | `--traces`, `--out` | `results/post_hoc/write_order.md` (re-resolves each shared key in run order and reverse order with `mam.systems.ours.Ours`) |
| [post_hoc_presentation.py](./post_hoc_presentation.py) | `plan`, `run` (paid), `counts`, `blind`, `join` | `results/post_hoc/presentation/`; `make_create` wraps the baselines named `*_meta` so each entry text gets a `[session N, author, kind] ` prefix |
| [post_hoc_paraphrase.py](./post_hoc_paraphrase.py) | `paraphrase` (paid), `run` (paid), `compare` | `results/post_hoc/paraphrase/` (`scenarios/`, `excluded.md`, `cost.json`, `comparison.md`); `configure_v2()` redirects to `results/post_hoc/paraphrase2` |
| [post_hoc_fresh.py](./post_hoc_fresh.py) | `plan`, `run` (paid), `criteria` | `results/post_hoc/fresh/` (`criteria.md`); `fresh_ids()` selects scenarios from `data/eval/manifest.json` |
| [post_hoc_ours2.py](./post_hoc_ours2.py) | `memory`, `compare`, `live` (paid), `criteria`, `memory3`, `compare3`; `--variant ours2/ours2_lite/ours3` | defines `Ours2` and `Ours3` (subclasses of `mam.systems.ours.Ours`); writes under `results/post_hoc/ours2/` and `results/post_hoc/ours3/` |
| [post_hoc_ours4.py](./post_hoc_ours4.py) | `paraphrase` (paid), `runA` (paid), `runB` (paid), `criteria` | defines `Ours4`, `ConstraintExtractor`, `ConstraintLLM`; `runA`/`runB` write under `results/post_hoc/ours4/` (including `constraints/<scenario>.json`); `paraphrase` calls `post_hoc_paraphrase.configure_v2()` and writes to `results/post_hoc/paraphrase2/` |

Further inputs and outputs not shown in the table:

- Inputs: `post_hoc_paraphrase.py compare` reads `results/post_hoc/fresh/units`; `post_hoc_fresh.py criteria`, `post_hoc_ours2.py criteria` and `post_hoc_ours4.py criteria` import `post_hoc_control_repeat`; `post_hoc_ours4.py criteria` also calls `post_hoc_paraphrase.configure_v2()` and reads `results/post_hoc/paraphrase2`, `results/post_hoc/fresh/units` and the `setA`/`setB` outputs; `post_hoc_presentation.py join` needs a hand-made `results/post_hoc/presentation/labels.json`; `post_hoc_c1c3.py join` needs `results/post_hoc/c1c3_labels.json` and asserts that it covers every answer.
- Outputs: `post_hoc_presentation.py` also writes `counts.md`, `blind.md`, `classified.md`; `post_hoc_ours2.py` writes `memory_level.md`, `criteria.md`, `criteria_lite.md` and `results/post_hoc/ours3/criteria.md`; `post_hoc_ours4.py criteria` writes `results/post_hoc/ours4/criteria.md`.
- `build_visual_demo.py` reads only the `ours` and `full_history` r0 files of `C1-eval-0000` and `C6-eval-0002` (plus the other cases in `CASES`); the editorial texts of `CASES` and the generated text of `post_hoc_write_order.py` are in Russian.
- `evidence_summary.py` uses the dictionaries `MEMORY_SYSTEMS` and `LIVE_SYSTEMS` (five systems each; the memory level uses the `@cache` variants for `ours` and `rolling_summary`).

### Tests

Each file below tests the script of the same name without the `test_` prefix, except `test_visual_demo.py`, which tests `build_visual_demo.py`:
[test_check_docs.py](./test_check_docs.py), [test_check_frozen_artifacts.py](./test_check_frozen_artifacts.py), [test_visual_demo.py](./test_visual_demo.py), [test_post_hoc_ours2.py](./test_post_hoc_ours2.py), [test_post_hoc_ours4.py](./test_post_hoc_ours4.py), [test_post_hoc_paraphrase.py](./test_post_hoc_paraphrase.py).

## Invariants

- `check_docs.py`, `check_frozen_artifacts.py`, `evidence_summary.py` and `build_visual_demo.py` use only the standard library and make no model or network calls. External links are not fetched (`check_docs.py` module docstring). Generated `results/` Markdown is not linted (`markdown_files`).
- `check_docs.py` lints only root `*.md` and `docs/**/*.md`, so the READMEs in `src/`, `src/mam/`, `src/mam/systems/`, `scripts/` and `external/` (and their links) are never checked. Besides local links, pinned links and `make <target>` mentions (unknown targets fail), it checks Mermaid `click ... href` directives (`MERMAID_URL`) and explicit `<a id>` anchors.
- `check_docs.py` validates GitHub links only when they match `PINNED_URL` (repository `avikhorev/multi-agent-memory`, commit hash, optional `#L<start>-L<end>` or heading anchor). A pinned link needs that commit in the local git history, otherwise `check_pinned` reports a missing snapshot.
- `check_frozen_artifacts.py` never rewrites the manifest (`--print-current` only prints). It accepts only manifest `schema` 1, rejects globs that are absolute or contain `..`, rejects duplicate globs, and raises `ValueError` for symlinks and non-regular files (`group_digest`, `validate`).
- `evidence_summary.py --verify` compares against hard-coded totals: memory level `EXPECTED_MEMORY` out of 780 checkpoints per system; live `EXPECTED_LIVE` out of 156 checkpoints and 42 units per system. A mismatch exits with 1. Without `--verify` it only prints and exits 0 (unless the saved results cannot be read).
- `build_visual_demo.py` takes the checkpoint cases from the `CASES` constant and the system set from `SYSTEMS` (`ours`, `full_history`), repeat `r0` only. `build_bundle` asserts that the trace agrees with the scored unit (pass flag, label, token count, answer) so the replay cannot show a label from another run. The generated file starts with a "do not edit by hand" header, and each `<` in the JSON is replaced by the six-character text `\u003c` (`render_js`).
- Fragile couplings: `post_hoc_ours4.py` depends on the private names `_EXTRACT_SYSTEM` and `_JSON_OBJECT` of `mam.extract` and asserts at import that two sentences of that prompt exist; `Ours2._resolve` depends on the trace reason text starting with `untrusted source`; `post_hoc_write_order.py` calls the private `Ours._resolve`. Decision thresholds are hard-coded in `post_hoc_ours2.py:criteria` (rejected <= 204, checks >= 134, strict factor >= 11; refute at > 270, <= 124, <= 9), `post_hoc_ours4.py:criteria` (5/6, 66, 96) and `post_hoc_fresh.py:criteria` (+-4, 5, 96).
- The `build_visual_demo.py` assertion in `build_bundle` fails with a plain `AssertionError`.
- The `post_hoc_*` scripts read their inputs from saved results. The subcommands that run variants replace `mam.live.create` (or `memory_eval.make_system` for the memory-level run in `post_hoc_ours2.py`) in the running process to inject variants; they do not edit `src/mam`.
- The paid subcommands that call `run_units` (`post_hoc_fresh.py run`, `post_hoc_ours2.py live`, `post_hoc_ours4.py runA|runB`, `post_hoc_paraphrase.py run`, `post_hoc_presentation.py run`) pass `--max-cost-usd` (and `--max-minutes`, except `post_hoc_ours4.py` and `post_hoc_paraphrase.py`, which fix it at the default `max_minutes` of 25) to `run_units`, print `done`, `skipped`, `failed`, `cost` and `stopped_by`, and exit with `sys.exit(r.exit_code)`. The `paraphrase` subcommands (`post_hoc_paraphrase.py`, `post_hoc_ours4.py`) go through `paraphrase_all(max_cost)`, which records each call's cost in `COST` and writes the total to `cost.json`; `paraphrase_all` does not read `max_cost` after its parameter list, so no cost cap is enforced there.
- Import setup: `post_hoc_c1c3.py`, `post_hoc_controls.py`, `post_hoc_control_repeat.py`, `post_hoc_write_order.py`, `post_hoc_presentation.py`, `post_hoc_paraphrase.py` and `post_hoc_fresh.py` insert `src` into `sys.path` themselves. `post_hoc_ours2.py` imports `mam` at module level without doing so, so `mam` must be importable (the Makefile uses `PYTHONPATH=src`; the editable install from `make venv` also works). `post_hoc_ours4.py` imports `post_hoc_ours2` and therefore has the same requirement.

## Side Effects

- Writes (without `--check`): `docs/demo/data.js` from `build_visual_demo.py`.
- Writes Markdown/JSON files under `results/post_hoc/` from the `post_hoc_*` scripts; the directories are created where the code calls `mkdir` (`post_hoc_c1c3.py`, `post_hoc_control_repeat.py`, `post_hoc_controls.py`, `post_hoc_ours4.py`, `post_hoc_paraphrase.py`).
- `check_docs.py` starts `git -C <root> show <ref>:<path>` subprocesses for pinned links.
- Paid subcommands (`post_hoc_fresh.py run`, `post_hoc_ours2.py live`, `post_hoc_ours4.py paraphrase|runA|runB`, `post_hoc_paraphrase.py paraphrase|run`, `post_hoc_presentation.py run`) call a model through `ClaudeCliClient`, spend money, and write per-unit results and traces into their output directories. `post_hoc_ours4.py` also writes the pinned-constraint listing per scenario (`Ours4.end_session`).
- `post_hoc_ours2.py memory` / `memory3` run `mam.memory_eval.main()` for the `eval` and `holdout` splits using `results/extraction/<split>/cache.jsonl`, and replace `sys.argv` and `memory_eval.make_system` in-process without restoring them.

## Verification

- Run: `make docs-check` (in Makefile order: `check_docs.py`; unittest `scripts.test_check_docs` and `scripts.test_check_frozen_artifacts`; `check_frozen_artifacts.py`; `evidence_summary.py --verify`; `build_visual_demo.py --check`; unittest `scripts.test_visual_demo`; stdlib only).
- Run (from the repository root): `python3 -m pytest scripts/test_post_hoc_ours2.py scripts/test_post_hoc_ours4.py scripts/test_post_hoc_paraphrase.py` (20 tests passed in a local run with system Python; these tests are not part of `make test`, whose `testpaths` is `tests`). The `test_post_hoc_ours2.py` docstring gives `pytest scripts/test_post_hoc_ours2.py`.
