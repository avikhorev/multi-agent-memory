# Control repeat against the committed run (repeat 0 on both sides; post hoc)

One repeat gives no intervals. Differences below are run-to-run variation plus any real change; this is a side-by-side comparison, not a statistical test.

## 1. Outcomes per category (checkpoints of the report table)

| category | system | main r0 | control | difference |
|---|---|---|---|---|
| C0 | full_history | 7/9 | 7/9 | 0 |
| C0 | ours | 7/9 | 5/9 | -2 |
| C0 | rolling_summary | 8/9 | 8/9 | 0 |
| C0 | shared_rag_bm25 | 8/9 | 6/9 | -2 |
| C0 | sliding_window | 7/9 | 7/9 | 0 |
| C1 | full_history | 0/3 | 0/3 | 0 |
| C1 | ours | 3/3 | 3/3 | 0 |
| C1 | rolling_summary | 0/3 | 0/3 | 0 |
| C1 | shared_rag_bm25 | 0/3 | 0/3 | 0 |
| C1 | sliding_window | 0/3 | 1/3 | 1 |
| C2 | full_history | 3/3 | 2/3 | -1 |
| C2 | ours | 3/3 | 3/3 | 0 |
| C2 | rolling_summary | 3/3 | 3/3 | 0 |
| C2 | shared_rag_bm25 | 3/3 | 3/3 | 0 |
| C2 | sliding_window | 3/3 | 3/3 | 0 |
| C3 | full_history | 0/3 | 1/3 | 1 |
| C3 | ours | 3/3 | 3/3 | 0 |
| C3 | rolling_summary | 1/3 | 0/3 | -1 |
| C3 | shared_rag_bm25 | 0/3 | 1/3 | 1 |
| C3 | sliding_window | 0/3 | 0/3 | 0 |
| C4 | full_history | 3/3 | 3/3 | 0 |
| C4 | ours | 3/3 | 3/3 | 0 |
| C4 | rolling_summary | 3/3 | 3/3 | 0 |
| C4 | shared_rag_bm25 | 3/3 | 3/3 | 0 |
| C4 | sliding_window | 3/3 | 3/3 | 0 |
| C5 | full_history | 3/3 | 3/3 | 0 |
| C5 | ours | 3/3 | 3/3 | 0 |
| C5 | rolling_summary | 3/3 | 3/3 | 0 |
| C5 | shared_rag_bm25 | 3/3 | 3/3 | 0 |
| C5 | sliding_window | 3/3 | 3/3 | 0 |
| C6 | full_history | 7/9 | 7/9 | 0 |
| C6 | ours | 6/9 | 8/9 | 2 |
| C6 | rolling_summary | 5/9 | 4/9 | -1 |
| C6 | shared_rag_bm25 | 7/9 | 9/9 | 2 |
| C6 | sliding_window | 4/9 | 4/9 | 0 |

## 2. All checkpoints of the repeat

| system | main r0 | control | difference |
|---|---|---|---|
| full_history | 56/78 | 57/78 | 1 |
| ours | 63/78 | 64/78 | 1 |
| rolling_summary | 59/78 | 55/78 | -4 |
| shared_rag_bm25 | 61/78 | 63/78 | 2 |
| sliding_window | 55/78 | 52/78 | -3 |

## 3. C1/C3 factor checkpoints: strict and lenient rule

| system | strict main r0 | strict control | lenient main r0 | lenient control |
|---|---|---|---|---|
| full_history | 0/6 | 1/6 | 5/6 | 5/6 |
| ours | 6/6 | 6/6 | 6/6 | 6/6 |
| rolling_summary | 1/6 | 0/6 | 5/6 | 4/6 |
| shared_rag_bm25 | 0/6 | 1/6 | 6/6 | 5/6 |
| sliding_window | 0/6 | 1/6 | 4/6 | 4/6 |

## 4. Input tokens per call on C6 by history length (all calls)

| system | main r0 | control |
|---|---|---|
| full_history | {10: 2308, 20: 4019, 30: 5246} | {10: 2360, 20: 3957, 30: 5823} |
| ours | {10: 1149, 20: 1452, 30: 1769} | {10: 1213, 20: 1312, 30: 1742} |
| rolling_summary | {10: 1729, 20: 2489, 30: 2775} | {10: 1548, 20: 2227, 30: 2650} |
| shared_rag_bm25 | {10: 2288, 20: 2659, 30: 2761} | {10: 2277, 20: 2573, 30: 2816} |
| sliding_window | {10: 2306, 20: 2666, 30: 2794} | {10: 2169, 20: 2660, 30: 2851} |

## 5. Cost per unit, USD

| system | main r0 | control | difference |
|---|---|---|---|
| full_history | 0.0328 | 0.034 | 0.0012 |
| ours | 0.0245 | 0.0234 | -0.0011 |
| rolling_summary | 0.0371 | 0.0361 | -0.0011 |
| shared_rag_bm25 | 0.028 | 0.0278 | -0.0002 |
| sliding_window | 0.028 | 0.0285 | 0.0005 |

## 6. Agent behaviour

| system | Worker read the offered source main r0 | control | Reviewer rejected main r0 | control | Planner update_record main r0 | control | Worker first update_record after it main r0 | control |
|---|---|---|---|---|---|---|---|---|
| full_history | 141/189 | 139/189 | 71/240 | 79/240 | 123 | 90 | 60 | 50 |
| ours | 101/189 | 95/189 | 154/240 | 160/240 | 121 | 123 | 86 | 88 |
| rolling_summary | 147/189 | 143/189 | 176/240 | 162/240 | 90 | 82 | 47 | 47 |
| shared_rag_bm25 | 150/189 | 125/189 | 48/240 | 62/240 | 116 | 123 | 52 | 73 |
| sliding_window | 136/189 | 130/189 | 79/240 | 69/240 | 106 | 103 | 58 | 64 |

