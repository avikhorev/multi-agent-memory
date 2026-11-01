| system | strict | lenient | n |
|---|---|---|---|
| **plain baselines, committed run (2 repeats)** | | | |
| full_history | 0 | 10 | 12 |
| sliding_window | 0 | 8 | 12 |
| shared_rag_bm25 | 0 | 11 | 12 |
| rolling_summary | 2 | 10 | 12 |
| ours | 12 | 12 | 12 |
| **with prefix, this check (2 repeats)** | | | |
| full_history | 3 | 10 | 12 |
| sliding_window | 2 | 8 | 12 |
| shared_rag_bm25 | 4 | 10 | 12 |
| rolling_summary | 2 | 7 | 12 |

## All checkpoints of the C1 and C3 scenarios (48 per system; supplement, not part of the D27 criterion)

| system | without prefix | with prefix | difference |
|---|---|---|---|
| full_history | 23/48 | 33/48 | +10 |
| sliding_window | 21/48 | 7/48 | -14 |
| shared_rag_bm25 | 23/48 | 27/48 | +4 |
| rolling_summary | 29/48 | 29/48 | +0 |
| ours (not rerun) | 37/48 | | |

Run-to-run spread on the 24 checks of one run (repeat 0 and repeat 1 of the main run, control run):

| system | main r0 | main r1 | control | min-max |
|---|---|---|---|---|
| full_history | 13 | 10 | 13 | 10-13 |
| sliding_window | 11 | 10 | 12 | 10-12 |
| shared_rag_bm25 | 13 | 10 | 14 | 10-14 |
| rolling_summary | 15 | 14 | 12 | 12-15 |
| ours | 19 | 18 | 19 | 18-19 |

Non-factor checkpoints (36 per system over both repeats), ok and label memory:

| system | ok without prefix | ok with prefix | memory label without prefix | memory label with prefix |
|---|---|---|---|---|
| full_history | 23/36 | 30/36 | 0 | 0 |
| sliding_window | 21/36 | 5/36 | 1 | 18 |
| shared_rag_bm25 | 23/36 | 23/36 | 0 | 0 |
| rolling_summary | 27/36 | 27/36 | 0 | 1 |

Sliding window on C1 scenarios: mean context items and tokens per memory read:

| variant | items | tokens | reads |
|---|---|---|---|
| plain, main run | 46.5 | 1226 | 180 |
| plain, control run | 46.2 | 1183 | 90 |
| with prefix | 37.4 | 1468 | 180 |
