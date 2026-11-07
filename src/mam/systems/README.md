# mam.systems

## Overview

The memory systems compared by the benchmark, all behind one interface (`MemorySystem` in `base.py`; the module docstring of `__init__.py` points to `docs/SCENARIO_FORMAT.md`, section 8). A system receives `Entry` objects through `write`, may digest them in `end_session`, and returns a token-limited `Context` for a `Reader` from `context`. The package holds the structured system under test (`ours`), four baselines (full history, sliding window, BM25 retrieval, rolling summary) and the shared BM25 ranking.

## Interface

Factory and registries (`__init__.py`):

- `create(name, *, limit=2000, ablate=frozenset(), extractor="oracle", cache_path=None, llm=None) -> MemorySystem`
- `NAMES = ("ours", "full_history", "sliding_window", "rolling_summary", "shared_rag_bm25")`
- `ABLATIONS = frozenset({"validity", "scopes", "trust", "pinned_constraints"})`
- `EXTRACTORS = ("oracle", "rules", "cache", "llm")`

Base (`base.py`):

- `MemorySystem(limit=2000)` with `write(entry)`, `end_session(session)`, `context(reader)` (raises `NotImplementedError` in the base class; there is no `abc`), `drain_llm_calls()`, `drain_extractions()`, `_visible(reader)`
- `visible_to(entry, reader) -> bool` is the scope filter
- `make_context(items) -> Context` sums `tokens.count` over item texts

Baselines (`baselines.py`):

- `FullHistory`, `SlidingWindow`, `SharedRagBm25`

Ranking (`ranking.py`):

- `tokenize(text)`, `bm25_scores(query, texts)` with constants `K1 = 1.5`, `B = 0.75`

Summaries (`summary.py`):

- `RollingSummary(limit, extractor, cache_path=None)`: one digest line per session from extracted facts
- `LLMSummary(limit, llm)`: summary written by the model once per session; exposes `refusals`, `summary_text`, `drain_llm_calls()`
- `CachedSummary(limit, cache_path)`: replays rows of kind `summary` from a cache file
- `clean_summary(text)`: drops lines that look like environment notes

Structured memory (`ours.py`):

- `Ours(limit, ablate=frozenset(), extractor="oracle", cache_path=None, llm=None)` with public attributes `quarantined`, `refusals`, `last_trace` and method `known_lines(text, k=8)`
- `Version` dataclass, `AUTHORITY = {"user": 3, "tool": 2, "document": 1, "agent": 0}`, `TRUST = {"trusted": 2, "agent": 1, "untrusted": 0}`

## Invariants

- `MemorySystem.write` ignores an entry whose id was already seen (`base.py:MemorySystem.write`); entries are expected in increasing clock order.
- The scope filter `visible_to` runs before any ranking or search: `private` is visible only to the author role, `task` only to the same `task_id`, other scopes to everyone (`base.py:visible_to`).
- `FullHistory` has no limit and never truncates; `SlidingWindow` walks the visible entries from newest to oldest and stops at the first one that does not fit `limit` (older, smaller entries are never used to fill the gap), then returns the kept entries in chronological order; `SharedRagBm25` returns items in rank order (score, then newest first), not chronological order, and skips items that do not fit (`baselines.py`).
- `create` rejects an unknown system, an extractor outside `EXTRACTORS`, an unknown ablation and ablations on any system other than `ours` (`__init__.py:create`). The checks for extractor `llm` without a client and extractor `cache` without `cache_path` exist in `create` only for `rolling_summary`; for `ours` they come from `mam.extract.make_extractor` (called in `Ours.__init__`); for `full_history`, `sliding_window` and `shared_rag_bm25` the `extractor`, `cache_path` and `llm` arguments are silently ignored. `rolling_summary` with extractor `oracle` is rejected (`summary.py:RollingSummary.__init__`).
- `Ours.context` puts pinned constraints first, de-duplicated by text, and raises `ValueError` if they alone exceed `limit` (`ours.py:Ours.context`). Facts and untrusted fragments are then ranked by BM25 against `reader.query` as two separate groups (ties: newer time or clock, then item id); all ranked facts are added before any fragment, and an item that does not fit is skipped while the loop continues.
- Version resolution per `(entity, attribute)` in write order (`ours.py:Ours._resolve`): first, a version with trust 0 (`untrusted`) is rejected whenever the current version has trust above 0 (`agent` or `trusted`), before any time or authority comparison; then a later event time wins; equal time falls back to source authority; equal authority leaves both versions as `[DISPUTED]`. A version with unknown time (`UNKNOWN_TIME`) gets time `latest + 1`, where `latest` is the maximum time among the earlier versions of that key in the visible set (so the first unknown-time version gets time 1); it is not tied to the write clock. A version with the same value as the current one replaces it when its source is more trusted.
- Untrusted tool output and documents are split by `guard.split_untrusted`; held fragments go to `quarantined` and are never added to the context. Fact items from untrusted sources get the `[data] ` prefix (`ours.py:Ours._fact_items`); fragment items (`frag-*`, built in `Ours.context`) have kind `quoted_data` but carry the bare fragment text with no prefix. A fragment is dropped when an extracted fact value appears in it (the fact represents it).
- Each ablation in `ABLATIONS` switches off one named mechanism of `Ours`: `validity`, `scopes`, `trust` or `pinned_constraints` (`ours.py`: checks of `self.ablate`). `trust` switches off several related things at once: no quarantine split (fragments go in whole, kind `raw`), no `[data]` quoting, no untrusted-override rejection, and pinned constraints are taken with `rule_constraints(require_trusted=False)` when the extractor returned none. `scopes` does not affect `known_lines`, which always excludes `private` entries.
- `RollingSummary` and `LLMSummary` skip `private` entries; the summaries drop their oldest lines first until the text fits `limit` (`summary.py:_TextSummary`, the shared base of `LLMSummary` and `CachedSummary`). `CachedSummary` replays cache rows, does not skip `private` entries, and uses the first task id that has a row for the session. `LLMSummary` asks the model for at most `int(limit * 0.5)` words; `clean_summary` also removes a "standing notes" header whose bullets were all dropped.

## Side Effects

- `LLMSummary.end_session` and `Ours` with extractor `llm` call `llm.complete`; the calls are queued and returned once by `drain_llm_calls()` (`summary.py:LLMSummary`, `ours.py:Ours.drain_llm_calls`).
- `CachedSummary.__init__` reads the cache file at `cache_path`; extractor `cache` does the same through `mam.extract.CacheExtractor`.
- `Ours.context` resets `last_trace` on every call, appends one `quarantine` op per quarantined fragment, and `Ours._resolve` appends `resolve` and `reject` ops (reasons `older event`, `lower authority`, `untrusted source cannot override a trusted fact`). `Ours.known_lines` (called from `_ingest` for extractors with `wants_known`, i.e. `llm`) also calls `_resolve`, so it appends to `last_trace` outside `context` without resetting it. `Ours.drain_extractions` returns the queued extraction records.
- State is held in memory only; no system writes to disk or the network by itself.

## Verification

- Run: `make test` (runs `.venv/bin/python -m pytest`; unit tests include `tests/unit/test_baselines.py`, `tests/unit/test_ours.py`, `tests/unit/test_ours_details.py`)
