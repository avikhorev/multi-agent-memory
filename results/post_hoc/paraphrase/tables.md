# Live layer results

Units: 36; systems: ours, ours3, shared_rag_bm25; repeats: 1. The sample is small: only large effects are visible. Counts and ranges over repeats, no intervals.

## Outcomes per system and category

| category | system | ok | range over repeats | ok given the information reached memory | ok % | agent % | memory % | model % | refusal % |
|---|---|---|---|---|---|---|---|---|---|
| C1 | ours | 2 of 3 | 0.67–0.67 | 2 of 3 | 67% | 0% | 33% | 0% | 0% |
| C1 | ours3 | 3 of 3 | 1.00–1.00 | 3 of 3 | 100% | 0% | 0% | 0% | 0% |
| C1 | shared_rag_bm25 | 0 of 3 | 0.00–0.00 | 0 of 3 | 0% | 0% | 100% | 0% | 0% |
| C2 | ours | 3 of 3 | 1.00–1.00 | 3 of 3 | 100% | 0% | 0% | 0% | 0% |
| C2 | ours3 | 3 of 3 | 1.00–1.00 | 3 of 3 | 100% | 0% | 0% | 0% | 0% |
| C2 | shared_rag_bm25 | 3 of 3 | 1.00–1.00 | 3 of 3 | 100% | 0% | 0% | 0% | 0% |
| C3 | ours | 3 of 3 | 1.00–1.00 | 3 of 3 | 100% | 0% | 0% | 0% | 0% |
| C3 | ours3 | 3 of 3 | 1.00–1.00 | 3 of 3 | 100% | 0% | 0% | 0% | 0% |
| C3 | shared_rag_bm25 | 1 of 3 | 0.33–0.33 | 1 of 3 | 33% | 0% | 67% | 0% | 0% |
| C6 | ours | 7 of 9 | 0.78–0.78 | 7 of 8 | 78% | 11% | 0% | 11% | 0% |
| C6 | ours3 | 8 of 9 | 0.89–0.89 | 8 of 9 | 89% | 0% | 0% | 11% | 0% |
| C6 | shared_rag_bm25 | 8 of 9 | 0.89–0.89 | 8 of 8 | 89% | 11% | 0% | 0% | 0% |

Labels are shares of the checkpoints; `refusal` is neither a successful attack nor a correct defence.

## Paired comparison with `ours` (same scenario, repeat and checkpoint)

| other system | category | only ours ok | only other ok | both ok | neither |
|---|---|---|---|---|---|
| ours3 | C1 | 0 | 1 | 2 | 0 |
| ours3 | C2 | 0 | 0 | 3 | 0 |
| ours3 | C3 | 0 | 0 | 3 | 0 |
| ours3 | C6 | 1 | 2 | 6 | 0 |
| shared_rag_bm25 | C1 | 2 | 0 | 0 | 1 |
| shared_rag_bm25 | C2 | 0 | 0 | 3 | 0 |
| shared_rag_bm25 | C3 | 2 | 0 | 1 | 0 |
| shared_rag_bm25 | C6 | 0 | 1 | 7 | 1 |

## Cost, tokens and time

| system | units | calls per unit | input tokens per call (all kinds) | output tokens per call | cost per call, USD | cost per unit, USD | model s per call | memory s per session | refusals |
|---|---|---|---|---|---|---|---|---|---|
| ours | 12 | 70.2 | 1346.9 | 272.9 | 0.000398465 | 0.027959 | 3.798 | 0.006637 | 0 |
| ours3 | 12 | 70.8 | 1685.7 | 250.0 | 0.000448698 | 0.031783 | 3.67 | 0.018452 | 0 |
| shared_rag_bm25 | 12 | 50.0 | 2460.0 | 292.0 | 0.000635824 | 0.031791 | 3.881 | 0.009309 | 0 |

## C6: growth with the length of the history

| system | input tokens per call at each length | cost per call at each length | slope, tokens per added session | slope, USD per added session |
|---|---|---|---|---|
| ours | 10: 1150, 20: 1524, 30: 1701 | 10: 0.000349, 20: 0.0004467, 30: 0.0005016 | 27.53 | 7.627e-06 |
| ours3 | 10: 1530, 20: 1763, 30: 2115 | 10: 0.0004095, 20: 0.0004713, 30: 0.0005559 | 29.22 | 7.32e-06 |
| shared_rag_bm25 | 10: 2117, 20: 2717, 30: 2845 | 10: 0.000594, 20: 0.0007036, 30: 0.0007251 | 36.41 | 6.56e-06 |
