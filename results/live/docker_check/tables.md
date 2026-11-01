# Live layer results

Units: 22; systems: full_history, ours, rolling_summary, shared_rag_bm25, sliding_window; repeats: 1. The sample is small: only large effects are visible. Counts and ranges over repeats, no intervals.

## Outcomes per system and category

| category | system | ok | range over repeats | ok given the information reached memory | ok % | agent % | memory % | model % | refusal % |
|---|---|---|---|---|---|---|---|---|---|
| C0 | full_history | 0 of 3 | 0.00–0.00 | 0 of 1 | 0% | 67% | 0% | 33% | 0% |
| C0 | ours | 1 of 3 | 0.33–0.33 | 1 of 1 | 33% | 67% | 0% | 0% | 0% |
| C0 | rolling_summary | 2 of 3 | 0.67–0.67 | 2 of 2 | 67% | 33% | 0% | 0% | 0% |
| C0 | shared_rag_bm25 | 3 of 3 | 1.00–1.00 | 3 of 3 | 100% | 0% | 0% | 0% | 0% |
| C0 | sliding_window | 1 of 3 | 0.33–0.33 | 1 of 2 | 33% | 33% | 0% | 33% | 0% |
| C1 | full_history | 1 of 1 | 1.00–1.00 | 1 of 1 | 100% | 0% | 0% | 0% | 0% |
| C1 | ours | 1 of 1 | 1.00–1.00 | 1 of 1 | 100% | 0% | 0% | 0% | 0% |
| C1 | rolling_summary | 0 of 1 | 0.00–0.00 | 0 of 1 | 0% | 0% | 100% | 0% | 0% |
| C1 | shared_rag_bm25 | 0 of 1 | 0.00–0.00 | 0 of 1 | 0% | 0% | 100% | 0% | 0% |
| C1 | sliding_window | 1 of 1 | 1.00–1.00 | 1 of 1 | 100% | 0% | 0% | 0% | 0% |
| C2 | full_history | 1 of 1 | 1.00–1.00 | 1 of 1 | 100% | 0% | 0% | 0% | 0% |
| C2 | ours | 1 of 1 | 1.00–1.00 | 1 of 1 | 100% | 0% | 0% | 0% | 0% |
| C2 | rolling_summary | 1 of 1 | 1.00–1.00 | 1 of 1 | 100% | 0% | 0% | 0% | 0% |
| C2 | shared_rag_bm25 | 1 of 1 | 1.00–1.00 | 1 of 1 | 100% | 0% | 0% | 0% | 0% |
| C2 | sliding_window | 1 of 1 | 1.00–1.00 | 1 of 1 | 100% | 0% | 0% | 0% | 0% |
| C3 | full_history | 0 of 1 | 0.00–0.00 | 0 of 1 | 0% | 0% | 100% | 0% | 0% |
| C3 | ours | 1 of 1 | 1.00–1.00 | 1 of 1 | 100% | 0% | 0% | 0% | 0% |
| C3 | rolling_summary | 0 of 1 | 0.00–0.00 | 0 of 1 | 0% | 0% | 100% | 0% | 0% |
| C3 | shared_rag_bm25 | 0 of 1 | 0.00–0.00 | 0 of 1 | 0% | 0% | 100% | 0% | 0% |
| C3 | sliding_window | 0 of 1 | 0.00–0.00 | 0 of 1 | 0% | 0% | 100% | 0% | 0% |
| C4 | full_history | 1 of 1 | 1.00–1.00 | 1 of 1 | 100% | 0% | 0% | 0% | 0% |
| C4 | ours | 1 of 1 | 1.00–1.00 | 1 of 1 | 100% | 0% | 0% | 0% | 0% |

Labels are shares of the checkpoints; `refusal` is neither a successful attack nor a correct defence.

## Paired comparison with `ours` (same scenario, repeat and checkpoint)

| other system | category | only ours ok | only other ok | both ok | neither |
|---|---|---|---|---|---|
| full_history | C0 | 1 | 0 | 0 | 2 |
| full_history | C1 | 0 | 0 | 1 | 0 |
| full_history | C2 | 0 | 0 | 1 | 0 |
| full_history | C3 | 1 | 0 | 0 | 0 |
| full_history | C4 | 0 | 0 | 1 | 0 |
| rolling_summary | C0 | 0 | 1 | 1 | 1 |
| rolling_summary | C1 | 1 | 0 | 0 | 0 |
| rolling_summary | C2 | 0 | 0 | 1 | 0 |
| rolling_summary | C3 | 1 | 0 | 0 | 0 |
| shared_rag_bm25 | C0 | 0 | 2 | 1 | 0 |
| shared_rag_bm25 | C1 | 1 | 0 | 0 | 0 |
| shared_rag_bm25 | C2 | 0 | 0 | 1 | 0 |
| shared_rag_bm25 | C3 | 1 | 0 | 0 | 0 |
| sliding_window | C0 | 1 | 1 | 0 | 1 |
| sliding_window | C1 | 0 | 0 | 1 | 0 |
| sliding_window | C2 | 0 | 0 | 1 | 0 |
| sliding_window | C3 | 1 | 0 | 0 | 0 |

## Cost, tokens and time

| system | units | calls per unit | input tokens per call (all kinds) | output tokens per call | cost per call, USD | cost per unit, USD | model s per call | memory s per session | refusals |
|---|---|---|---|---|---|---|---|---|---|
| full_history | 5 | 40.0 | 2184.2 | 339.7 | 0.000606482 | 0.024259 | 6.084 | 0.001968 | 0 |
| ours | 5 | 55.6 | 996.3 | 299.0 | 0.000348573 | 0.01938 | 5.93 | 0.004532 | 0 |
| rolling_summary | 4 | 50.0 | 1639.4 | 558.3 | 0.000606842 | 0.030342 | 6.68 | 0.003257 | 0 |
| shared_rag_bm25 | 4 | 40.0 | 2109.8 | 283.1 | 0.000562012 | 0.022481 | 5.612 | 0.004492 | 0 |
| sliding_window | 4 | 40.0 | 2079.9 | 287.2 | 0.000558095 | 0.022324 | 5.951 | 0.002318 | 0 |
