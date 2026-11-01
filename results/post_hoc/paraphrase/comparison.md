# Paraphrase check: checks passed on the original and on the paraphrased scenarios (same systems, same scenarios)

| system | group | original | paraphrased | loss |
|---|---|---|---|---|
| ours | C2 (3 constraint checks + 9 value checks) | 11/12 | 9/12 | 18% |
| ours | C1/C3 | 21/24 | 19/24 | 10% |
| ours | C6 | 8/9 | 7/9 | 12% |
| ours | all | 40/45 | 35/45 | 12% |
| ours3 | C2 (3 constraint checks + 9 value checks) | 10/12 | 12/12 | -20% |
| ours3 | C1/C3 | 21/24 | 22/24 | -5% |
| ours3 | C6 | 9/9 | 8/9 | 11% |
| ours3 | all | 40/45 | 42/45 | -5% |
| shared_rag_bm25 | C2 (3 constraint checks + 9 value checks) | 10/12 | 10/12 | 0% |
| shared_rag_bm25 | C1/C3 | 16/24 | 17/24 | -6% |
| shared_rag_bm25 | C6 | 8/9 | 8/9 | 0% |
| shared_rag_bm25 | all | 34/45 | 35/45 | -3% |

## Corrected count: a constraint check with an update_record action counts as failed (decision D39)

| system | original, corrected | paraphrased, corrected | loss | constraint checks with update_record: original | paraphrased |
|---|---|---|---|---|---|
| ours | 40/45 | 32/45 | 20% | 0 | 3 |
| ours3 | 40/45 | 42/45 | -5% | 0 | 0 |
| shared_rag_bm25 | 34/45 | 35/45 | -3% | 0 | 0 |

## Does the rule that pins constraints fire on the constraint messages?

| scenario | original | paraphrased |
|---|---|---|
| C2-eval-0003 | [True] | [False] |
| C2-eval-0004 | [True] | [False] |
| C2-eval-0005 | [True] | [False] |

Verdict for ours3 (loss on the sum of the four groups, thresholds 10% and 25%): robust; corrected count: ours3 robust, ours partial.
