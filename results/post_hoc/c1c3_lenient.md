| system | n | strict | lenient (expected value present, stale mention allowed) |
|---|---|---|---|
| full_history | 12 | 0 | 10 |
| ours | 12 | 12 | 12 |
| rolling_summary | 12 | 2 | 10 |
| shared_rag_bm25 | 12 | 0 | 11 |
| sliding_window | 12 | 0 | 8 |

Baseline failures under the strict rule: 46; of them the answer contains the expected value: 37.
