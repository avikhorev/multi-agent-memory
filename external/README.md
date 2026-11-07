# external

## Overview

External baselines for the benchmark (decision D42). The folder holds adapters that wrap two third-party memory libraries, Mem0 and Graphiti, as `mam` memory systems, a runner (`run.py`) that plugs an adapter into the benchmark and compares it with the project's own systems, and one smoke test per adapter. Both adapters use the benchmark's own model client (Haiku through `ClaudeCliClient`) as the library's LLM, a local fastembed embedder (`BAAI/bge-small-en-v1.5`, 384 dimensions) and stores in temporary local folders. Nothing in the project imports this folder (`run.py` docstring).

Each adapter has its own requirements file and, by the comments in the smoke tests, its own virtualenv (`external/.venv-mem0`, `external/.venv-graphiti`, ignored by `.gitignore`).

## Interface

- `run.py` - CLI: `python external/run.py <system> pilot|run|tables|common [--max-cost-usd X] [--fresh-cats C1,C3] [--only SET]` (`--max-cost-usd` default `1.0`). `<system>` is the prefix of an `<system>_adapter` module in this folder (`mem0`, `graphiti`).
  - `pilot`: one scenario (`C2-eval-0003`) from `data/eval`.
  - `run`: the sets from `sets()`, `fresh` (`data/eval` with ids from `post_hoc_fresh.fresh_ids()`) and `paraphrase2` (`results/post_hoc/paraphrase2/scenarios`, ids `C2-eval-0006..0011` and `C5-eval-0006..0008`).
  - `--fresh-cats` applies to every set (`pilot`, `fresh` and `paraphrase2`), not only to `fresh`; `--only` filters by set name (`pilot`, `fresh`, `paraphrase2`).
  - Exit status: `run.py` prints the `run_units` report but never calls `sys.exit(r.exit_code)`, so incomplete runs, failures and rate-limit stops all end with status 0.
  - `tables` and `common` print rows only for sets where the external system already has a `units` folder and only for rivals whose `units` folder exists (`results/post_hoc/fresh`, `ours4/setB`, `ours4/setA`); `stats` reads `traces/<unit>.jsonl` for every unit, so a missing trace file raises.
  - `tables`: writes `tables.md` under `results/post_hoc/external/<system>/` and prints it; `common` writes `common12.md` (the 12 scenarios of D43: C1 and C3 of set `fresh`, C2 of set `paraphrase2`).
  - Functions: `sets()`, `stats(base, system, ids=None)`, `tables(system, cats=None, fname="tables.md")`; constants `OUT`, `R`, `A_IDS`, `RIVALS` (the project systems each external system is compared with).
- `mem0_adapter.py`
  - `create(limit, llm)` returns `Mem0`, a `mam.systems.base.MemorySystem`.
  - `Mem0.end_session(session)`, `Mem0.drain_llm_calls()`, `Mem0.context(reader)`.
  - `ClientLLM.generate_response(...)` is the model object that Mem0 calls; it is routed to the benchmark client.
- `graphiti_adapter.py`
  - `create(limit, llm)` returns `Graphiti3`, a `mam.systems.base.MemorySystem`.
  - `Graphiti3.end_session(session)`, `Graphiti3.drain_llm_calls()`, `Graphiti3.context(reader)`.
  - Helpers: `ClientLLM` (`graphiti_core` `LLMClient` over the benchmark client), `Embedder` (fastembed), `Flat` (no-op cross encoder), `shape(s, defs)` (placeholder instance of a JSON schema).
- `requirements-mem0.txt` - `mem0ai==2.2.1`, `fastembed==0.9.1`, `pytest`.
- `requirements-graphiti.txt` - `graphiti-core[kuzu]==0.31.2`, `fastembed==0.9.1`, `pytest`.
- `test_mem0_smoke.py`, `test_graphiti_smoke.py` - smoke tests with a stub model (`mam.llm.FakeClient`).

## Invariants

- Records reach the library only at `end_session(session)`, and each entry id is sent once (`_sent` set in both adapters). Graphiti sends entries in `clock` order; Mem0 sends one group at a time in order of first appearance, so entries of different groups are not sent in global clock order.
- Mem0: one `Memory.add()` per `(task_id, scope, author)` group of the session, with `user_id=task_id`; per the module docstring, `add()` only adds memories (event ADD) in library version 2.2.1.
- Graphiti: one `add_episode` per entry, with `reference_time = BASE_DAY (2026-01-01 UTC) + clock days`.
- Mem0 `context(reader)` never returns an entry with `scope == "private"` whose author is not `reader.role` (it checks `metadata`). Graphiti `context` hides such raw episodes (`Graphiti3.eid` maps episode uuid to entry) and drops edges whose episodes are all hidden, but keeps an edge when at least one episode is visible or the edge has no episode list, and adds every node summary (`n.summary for n in r.nodes`) without filtering, so text derived from a hidden private episode can still reach the context. The context holds valid facts (edges), node summaries and raw episodes. Items are added while the running `count(text)` stays within `limit`, so the token count does not exceed `limit`.
- Mem0 `context` searches with `filters={"user_id": reader.task_id}`, `top_k=20`, `threshold=0.0`. Graphiti `context` uses the library's default `search_` and skips edges with `invalid_at` or `expired_at`.
- Every model call made by a library is appended to `calls` as `("memory", out)`; `drain_llm_calls()` returns them and clears the list. A refusal yields `""` (Mem0) or `{}` (Graphiti).
- Mem0 configures the placeholder LLM provider `vllm` and replaces `Memory.llm` after construction; its vector store uses `embedding_model_dims=384` and `on_disk=True` with a `history_db_path`. Graphiti `ClientLLM` runs the benchmark client in a thread-pool executor and returns `{}` on a refusal or when no JSON span is found; `Embedder.create` joins non-string input with spaces; `BASE_DAY` is a module constant.
- Graphiti requests are answered as one JSON object in the shape given by `shape()`; the adapter parses the first `{...}` span of the reply.
- `run.py` replaces the system by patching `mam.live.create`; default `limit` is `2000`. Runs use `workers=8`, `max_minutes=25` and the given `--max-cost-usd`.
- Graphiti needs `EMBEDDING_DIM=384`; the adapter sets it (and `GRAPHITI_TELEMETRY_ENABLED=false`) in `os.environ` before importing the library. Mem0 sets `MEM0_TELEMETRY=False`.

## Side Effects

- Both adapters create temporary folders with `tempfile.mkdtemp` (`mem0-*` with Qdrant on disk and `history.db`; `graphiti-*/kuzu.db`) and do not remove them.
- Graphiti `__init__` runs `INSTALL fts`, `LOAD EXTENSION fts` and the library's full-text index queries on the Kuzu database.
- fastembed downloads the `BAAI/bge-small-en-v1.5` model on first use (the Mem0 smoke test names it as its only network access, since the model is a stub there).
- `Embedder.model` in `graphiti_adapter.py` loads the embedding model at import time.
- `run.py` inserts `src`, `external` and `scripts` of the repository root into `sys.path`; it calls the model through `ClaudeCliClient` (costs money, bounded by `--max-cost-usd`) and writes unit results and traces under `results/post_hoc/external/<system>/<set>/`, plus the table files named above.

## Verification

- Mem0 smoke test: `PYTHONPATH=src:external external/.venv-mem0/bin/python -m pytest external/test_mem0_smoke.py -q`
- Graphiti smoke test: `EMBEDDING_DIM=384 PYTHONPATH=src:external external/.venv-graphiti/bin/python -m pytest external/test_graphiti_smoke.py -q`
- The tests skip (`pytest.importorskip("mam")`) when `mam` is not importable. The main project suite is `make test` (`python -m pytest`, `testpaths = ["tests"]`) and does not include this folder.
