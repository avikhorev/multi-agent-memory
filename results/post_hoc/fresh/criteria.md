# Fresh scenarios: ours3 against the others (preset criteria of D37)

| system | all checks ok | strict factor C1/C3 | Reviewer rejected | cost per unit, USD | units |
|---|---|---|---|---|---|
| ours | 71/78 | 5/6 | 150/240 | 0.0236 | 21 |
| ours3 | 70/78 | 6/6 | 62/240 | 0.0270 | 21 |
| shared_rag_bm25 | 62/78 | 1/6 | 68/240 | 0.0281 | 21 |
| full_history | 62/78 | 1/6 | 71/240 | 0.0329 | 21 |
| full_history_meta | 67/78 | 2/6 | 54/240 | 0.0402 | 21 |

Lead of ours3 in checks: ours -1, shared_rag_bm25 +8, full_history_meta +3
Verdict: neither (differences within the +-4 spread or a criterion not met).
