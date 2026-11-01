# Controls (additional analysis after the freeze)

## 1. Agent behaviour per system (same prompts for all systems)

Planner chose update_record, and what the Worker did first in those sessions:

| system | Planner chose update_record (sessions) | Worker's first action was update_record | Worker called update_record in either call |
|---|---|---|---|
| full_history | 234 | 128 | 170 |
| ours | 237 | 169 | 186 |
| rolling_summary | 182 | 97 | 123 |
| shared_rag_bm25 | 206 | 101 | 152 |
| sliding_window | 222 | 123 | 167 |

| system | Worker read the offered source (sessions with a source) | of them on C6 | first action update_record (offered source) | Reviewer rejected | rejected in sessions 5+ |
|---|---|---|---|---|---|
| full_history | 264 of 378 | 68 of 92 | 104 | 146 of 480 | 78 of 312 |
| ours | 199 of 378 | 40 of 92 | 167 | 306 of 480 | 181 of 312 |
| rolling_summary | 284 of 378 | 69 of 92 | 85 | 343 of 480 | 192 of 312 |
| shared_rag_bm25 | 291 of 378 | 66 of 92 | 73 | 112 of 480 | 56 of 312 |
| sliding_window | 264 of 378 | 61 of 92 | 104 | 178 of 480 | 111 of 312 |

## 2. Memory-level failures on eval by kind of violation

| system | category | violations of the failed check | failed checks |
|---|---|---|---|
| full_history | C1 | absent found | 12 |
| full_history | C1 | absent found + present missing | 18 |
| full_history | C3 | absent found | 8 |
| full_history | C3 | absent found + present missing | 6 |
| full_history | C3 | disputed pair | 6 |
| full_history | C5 | outside quoted data | 30 |
| full_history | all | total failures | 80 |
| sliding_window | C1 | absent found | 12 |
| sliding_window | C1 | absent found + present missing | 18 |
| sliding_window | C3 | absent found | 8 |
| sliding_window | C3 | absent found + present missing | 6 |
| sliding_window | C3 | disputed pair | 6 |
| sliding_window | C5 | outside quoted data | 30 |
| sliding_window | C6 | present missing | 40 |
| sliding_window | all | total failures | 120 |
| shared_rag_bm25 | C1 | absent found | 12 |
| shared_rag_bm25 | C1 | absent found + present missing | 18 |
| shared_rag_bm25 | C3 | absent found | 8 |
| shared_rag_bm25 | C3 | absent found + present missing | 6 |
| shared_rag_bm25 | C3 | disputed pair | 6 |
| shared_rag_bm25 | C5 | outside quoted data | 30 |
| shared_rag_bm25 | all | total failures | 80 |
| rolling_summary@cache | C1 | absent found | 22 |
| rolling_summary@cache | C1 | absent found + present missing | 8 |
| rolling_summary@cache | C3 | absent found | 18 |
| rolling_summary@cache | C3 | absent found + present missing | 1 |
| rolling_summary@cache | C3 | disputed pair | 6 |
| rolling_summary@cache | C5 | outside quoted data | 7 |
| rolling_summary@cache | C6 | present missing | 21 |
| rolling_summary@cache | all | total failures | 83 |
| ours@cache | C1 | absent found + present missing | 1 |
| ours@cache | C4 | present missing | 1 |
| ours@cache | all | total failures | 2 |

## 3. Write-side cost and time per unit (model calls made by the memory itself)

| system | memory calls per unit | input tokens per unit | memory model time per unit, s | memory cost per unit, USD | memory model time per session, s | agent model time per unit, s | all model time per unit, s |
|---|---|---|---|---|---|---|---|
| full_history | 0.0 | 0 | 0.0 | 0.0 | 0.0 | 164.9 | 164.9 |
| ours | 17.3 | 18978 | 48.5 | 0.0042 | 4.25 | 178.6 | 227.1 |
| rolling_summary | 11.4 | 24018 | 68.3 | 0.0121 | 5.97 | 177.4 | 245.7 |
| shared_rag_bm25 | 0.0 | 0 | 0.0 | 0.0 | 0.0 | 164.3 | 164.3 |
| sliding_window | 0.0 | 0 | 0.0 | 0.0 | 0.0 | 166.8 | 166.8 |

C0 only (short histories), all calls:

| system | calls per unit | model time per unit, s | cost per unit, USD | ok | checkpoints |
|---|---|---|---|---|---|
| full_history | 40.0 | 154.6 | 0.0246 | 12 | 18 |
| ours | 53.8 | 199.9 | 0.0191 | 13 | 18 |
| rolling_summary | 50.0 | 205.3 | 0.0276 | 16 | 18 |
| shared_rag_bm25 | 40.2 | 151.9 | 0.0236 | 15 | 18 |
| sliding_window | 40.0 | 149.8 | 0.0236 | 15 | 18 |

C0: ours vs full_history, calls +35%, model time +29%.

## 4. Live outcome totals

| system | all checkpoints ok | of | checkpoints in the headline table ok | of | all except the factor checkpoints of C1 and C3 ok | of |
|---|---|---|---|---|---|---|
| full_history | 108 | 156 | 45 | 66 | 108 | 144 |
| ours | 124 | 156 | 55 | 66 | 112 | 144 |
| rolling_summary | 119 | 156 | 47 | 66 | 117 | 144 |
| shared_rag_bm25 | 117 | 156 | 47 | 66 | 117 | 144 |
| sliding_window | 104 | 156 | 42 | 66 | 104 | 144 |

## 5. Input tokens per call on C6 by history length, agent calls only

| system | length 10 | length 20 | length 30 | slope, tokens per added session |
|---|---|---|---|---|
| full_history | 10: 2361 | 20: 3801 | 30: 5478 | 155.8 |
| ours | 10: 1176 | 20: 1458 | 30: 1916 | 37.0 |
| rolling_summary | 10: 1659 | 20: 2276 | 30: 2638 | 48.9 |
| shared_rag_bm25 | 10: 2301 | 20: 2667 | 30: 2800 | 24.9 |
| sliding_window | 10: 2300 | 20: 2655 | 30: 2813 | 25.6 |

Units per category for one system (scenarios x repeats): C0 6, C1 6, C2 6, C3 6, C4 6, C5 6, C6 6.

## 6. Implicit-update extraction: value written in the message or computed

| split | implicit updates with the value written in the message | found | implicit updates with a computed value | found |
|---|---|---|---|---|
| eval | 20 | 20 | 40 | 39 |
| holdout | 2 | 2 | 8 | 8 |
