# Live layer results

Units: 210; systems: full_history, ours, rolling_summary, shared_rag_bm25, sliding_window; repeats: 2. The sample is small: only large effects are visible. Counts and ranges over repeats, no intervals.

## Outcomes per system and category

| category | system | ok | range over repeats | ok given the information reached memory | ok % | agent % | memory % | model % | refusal % |
|---|---|---|---|---|---|---|---|---|---|
| C0 | full_history | 12 of 18 | 0.56–0.78 | 12 of 14 | 67% | 22% | 0% | 11% | 0% |
| C0 | ours | 13 of 18 | 0.67–0.78 | 13 of 14 | 72% | 22% | 0% | 6% | 0% |
| C0 | rolling_summary | 16 of 18 | 0.89–0.89 | 16 of 16 | 89% | 11% | 0% | 0% | 0% |
| C0 | shared_rag_bm25 | 15 of 18 | 0.78–0.89 | 15 of 16 | 83% | 11% | 0% | 6% | 0% |
| C0 | sliding_window | 15 of 18 | 0.78–0.89 | 15 of 15 | 83% | 17% | 0% | 0% | 0% |
| C1 | full_history | 0 of 6 | 0.00–0.00 | 0 of 6 | 0% | 0% | 100% | 0% | 0% |
| C1 | ours | 6 of 6 | 1.00–1.00 | 6 of 6 | 100% | 0% | 0% | 0% | 0% |
| C1 | rolling_summary | 0 of 6 | 0.00–0.00 | 0 of 6 | 0% | 0% | 100% | 0% | 0% |
| C1 | shared_rag_bm25 | 0 of 6 | 0.00–0.00 | 0 of 6 | 0% | 0% | 100% | 0% | 0% |
| C1 | sliding_window | 0 of 6 | 0.00–0.00 | 0 of 6 | 0% | 0% | 100% | 0% | 0% |
| C2 | full_history | 6 of 6 | 1.00–1.00 | 6 of 6 | 100% | 0% | 0% | 0% | 0% |
| C2 | ours | 6 of 6 | 1.00–1.00 | 6 of 6 | 100% | 0% | 0% | 0% | 0% |
| C2 | rolling_summary | 6 of 6 | 1.00–1.00 | 6 of 6 | 100% | 0% | 0% | 0% | 0% |
| C2 | shared_rag_bm25 | 6 of 6 | 1.00–1.00 | 6 of 6 | 100% | 0% | 0% | 0% | 0% |
| C2 | sliding_window | 6 of 6 | 1.00–1.00 | 6 of 6 | 100% | 0% | 0% | 0% | 0% |
| C3 | full_history | 0 of 6 | 0.00–0.00 | 0 of 6 | 0% | 0% | 67% | 33% | 0% |
| C3 | ours | 6 of 6 | 1.00–1.00 | 6 of 6 | 100% | 0% | 0% | 0% | 0% |
| C3 | rolling_summary | 2 of 6 | 0.33–0.33 | 2 of 6 | 33% | 0% | 67% | 0% | 0% |
| C3 | shared_rag_bm25 | 0 of 6 | 0.00–0.00 | 0 of 6 | 0% | 0% | 67% | 33% | 0% |
| C3 | sliding_window | 0 of 6 | 0.00–0.00 | 0 of 6 | 0% | 0% | 67% | 33% | 0% |
| C4 | full_history | 6 of 6 | 1.00–1.00 | 6 of 6 | 100% | 0% | 0% | 0% | 0% |
| C4 | ours | 6 of 6 | 1.00–1.00 | 6 of 6 | 100% | 0% | 0% | 0% | 0% |
| C4 | rolling_summary | 6 of 6 | 1.00–1.00 | 6 of 6 | 100% | 0% | 0% | 0% | 0% |
| C4 | shared_rag_bm25 | 6 of 6 | 1.00–1.00 | 6 of 6 | 100% | 0% | 0% | 0% | 0% |
| C4 | sliding_window | 6 of 6 | 1.00–1.00 | 6 of 6 | 100% | 0% | 0% | 0% | 0% |
| C5 | full_history | 6 of 6 | 1.00–1.00 | 6 of 6 | 100% | 0% | 0% | 0% | 0% |
| C5 | ours | 6 of 6 | 1.00–1.00 | 6 of 6 | 100% | 0% | 0% | 0% | 0% |
| C5 | rolling_summary | 6 of 6 | 1.00–1.00 | 6 of 6 | 100% | 0% | 0% | 0% | 0% |
| C5 | shared_rag_bm25 | 6 of 6 | 1.00–1.00 | 6 of 6 | 100% | 0% | 0% | 0% | 0% |
| C5 | sliding_window | 6 of 6 | 1.00–1.00 | 6 of 6 | 100% | 0% | 0% | 0% | 0% |
| C6 | full_history | 15 of 18 | 0.78–0.89 | 15 of 16 | 83% | 11% | 0% | 6% | 0% |
| C6 | ours | 12 of 18 | 0.67–0.67 | 12 of 12 | 67% | 33% | 0% | 0% | 0% |
| C6 | rolling_summary | 11 of 18 | 0.56–0.67 | 11 of 16 | 61% | 11% | 22% | 6% | 0% |
| C6 | shared_rag_bm25 | 14 of 18 | 0.78–0.78 | 14 of 16 | 78% | 11% | 6% | 6% | 0% |
| C6 | sliding_window | 9 of 18 | 0.44–0.56 | 9 of 17 | 50% | 6% | 39% | 6% | 0% |

Labels are shares of the checkpoints; `refusal` is neither a successful attack nor a correct defence.

## Paired comparison with `ours` (same scenario, repeat and checkpoint)

| other system | category | only ours ok | only other ok | both ok | neither |
|---|---|---|---|---|---|
| full_history | C0 | 3 | 2 | 10 | 3 |
| full_history | C1 | 6 | 0 | 0 | 0 |
| full_history | C2 | 0 | 0 | 6 | 0 |
| full_history | C3 | 6 | 0 | 0 | 0 |
| full_history | C4 | 0 | 0 | 6 | 0 |
| full_history | C5 | 0 | 0 | 6 | 0 |
| full_history | C6 | 1 | 4 | 11 | 2 |
| rolling_summary | C0 | 1 | 4 | 12 | 1 |
| rolling_summary | C1 | 6 | 0 | 0 | 0 |
| rolling_summary | C2 | 0 | 0 | 6 | 0 |
| rolling_summary | C3 | 4 | 0 | 2 | 0 |
| rolling_summary | C4 | 0 | 0 | 6 | 0 |
| rolling_summary | C5 | 0 | 0 | 6 | 0 |
| rolling_summary | C6 | 5 | 4 | 7 | 2 |
| shared_rag_bm25 | C0 | 2 | 4 | 11 | 1 |
| shared_rag_bm25 | C1 | 6 | 0 | 0 | 0 |
| shared_rag_bm25 | C2 | 0 | 0 | 6 | 0 |
| shared_rag_bm25 | C3 | 6 | 0 | 0 | 0 |
| shared_rag_bm25 | C4 | 0 | 0 | 6 | 0 |
| shared_rag_bm25 | C5 | 0 | 0 | 6 | 0 |
| shared_rag_bm25 | C6 | 1 | 3 | 11 | 3 |
| sliding_window | C0 | 1 | 3 | 12 | 2 |
| sliding_window | C1 | 6 | 0 | 0 | 0 |
| sliding_window | C2 | 0 | 0 | 6 | 0 |
| sliding_window | C3 | 6 | 0 | 0 | 0 |
| sliding_window | C4 | 0 | 0 | 6 | 0 |
| sliding_window | C5 | 0 | 0 | 6 | 0 |
| sliding_window | C6 | 6 | 3 | 6 | 3 |

## Cost, tokens and time

| system | units | calls per unit | input tokens per call (all kinds) | output tokens per call | cost per call, USD | cost per unit, USD | model s per call | memory s per session | refusals |
|---|---|---|---|---|---|---|---|---|---|
| full_history | 42 | 45.7 | 2915.6 | 277.6 | 0.000720274 | 0.032927 | 3.606 | 0.003289 | 0 |
| ours | 42 | 63.0 | 1262.8 | 269.8 | 0.000375887 | 0.02369 | 3.604 | 0.005323 | 0 |
| rolling_summary | 42 | 57.2 | 1916.6 | 522.7 | 0.000642452 | 0.036727 | 4.298 | 0.009283 | 0 |
| shared_rag_bm25 | 42 | 45.8 | 2382.1 | 273.9 | 0.000610446 | 0.027935 | 3.59 | 0.007877 | 0 |
| sliding_window | 42 | 45.7 | 2402.8 | 275.2 | 0.000615182 | 0.028123 | 3.649 | 0.004448 | 0 |

## C6: growth with the length of the history

| system | input tokens per call at each length | cost per call at each length | slope, tokens per added session | slope, USD per added session |
|---|---|---|---|---|
| full_history | 10: 2361, 20: 3801, 30: 5478 | 10: 0.0005955, 20: 0.0008926, 30: 0.001232 | 155.8 | 3.18e-05 |
| ours | 10: 1152, 20: 1378, 30: 1717 | 10: 0.00033, 20: 0.000415, 30: 0.0004871 | 28.26 | 7.856e-06 |
| rolling_summary | 10: 1679, 20: 2352, 30: 2809 | 10: 0.0005568, 20: 0.0007875, 30: 0.000977 | 56.47 | 2.101e-05 |
| shared_rag_bm25 | 10: 2301, 20: 2667, 30: 2800 | 10: 0.0005916, 20: 0.0006558, 30: 0.0006908 | 24.94 | 4.96e-06 |
| sliding_window | 10: 2300, 20: 2655, 30: 2813 | 10: 0.0005698, 20: 0.0006589, 30: 0.000696 | 25.63 | 6.31e-06 |

## C5: exposure to the attack

| system | units | the Worker read the attack document | attacked (all units) | attacked (among those who read it) |
|---|---|---|---|---|
| full_history | 6 | 3 | 0 | 0 of 3 |
| ours | 6 | 2 | 0 | 0 of 2 |
| rolling_summary | 6 | 3 | 0 | 0 of 3 |
| shared_rag_bm25 | 6 | 3 | 0 | 0 of 3 |
| sliding_window | 6 | 2 | 0 | 0 of 2 |
