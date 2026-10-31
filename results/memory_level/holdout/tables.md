# holdout, memory level

### C0: correct

| system |  |
|---|
| full_history |  |
| sliding_window |  |
| shared_rag_bm25 |  |
| rolling_summary@rules |  |
| ours@oracle |  |
| ours@rules |  |
| ours@oracle-no_validity |  |
| ours@oracle-no_scopes |  |
| ours@oracle-no_trust |  |
| ours@oracle-no_pinned_constraints |  |
| rolling_summary@cache |  |
| ours@cache |  |
| ours@cache-no_validity |  |
| ours@cache-no_scopes |  |
| ours@cache-no_trust |  |
| ours@cache-no_pinned_constraints |  |

### C1: current value present

| system | variant=implicit (n=3) |
|---|---|
| full_history | 0.00 [0.00, 0.00] |
| sliding_window | 0.00 [0.00, 0.00] |
| shared_rag_bm25 | 0.00 [0.00, 0.00] |
| rolling_summary@rules | 0.00 [0.00, 0.00] |
| ours@oracle | 1.00 [1.00, 1.00] |
| ours@rules | 0.00 [0.00, 0.00] |
| ours@oracle-no_validity | 1.00 [1.00, 1.00] |
| ours@oracle-no_scopes | 1.00 [1.00, 1.00] |
| ours@oracle-no_trust | 1.00 [1.00, 1.00] |
| ours@oracle-no_pinned_constraints | 1.00 [1.00, 1.00] |
| rolling_summary@cache | 0.33 [0.00, 1.00] |
| ours@cache | 1.00 [1.00, 1.00] |
| ours@cache-no_validity | 1.00 [1.00, 1.00] |
| ours@cache-no_scopes | 1.00 [1.00, 1.00] |
| ours@cache-no_trust | 1.00 [1.00, 1.00] |
| ours@cache-no_pinned_constraints | 1.00 [1.00, 1.00] |

### C1: stale value shown

| system | variant=implicit (n=3) |
|---|---|
| full_history | 1.00 [1.00, 1.00] |
| sliding_window | 1.00 [1.00, 1.00] |
| shared_rag_bm25 | 1.00 [1.00, 1.00] |
| rolling_summary@rules | 1.00 [1.00, 1.00] |
| ours@oracle | 0.00 [0.00, 0.00] |
| ours@rules | 1.00 [1.00, 1.00] |
| ours@oracle-no_validity | 1.00 [1.00, 1.00] |
| ours@oracle-no_scopes | 0.00 [0.00, 0.00] |
| ours@oracle-no_trust | 0.33 [0.00, 1.00] |
| ours@oracle-no_pinned_constraints | 0.00 [0.00, 0.00] |
| rolling_summary@cache | 1.00 [1.00, 1.00] |
| ours@cache | 0.00 [0.00, 0.00] |
| ours@cache-no_validity | 1.00 [1.00, 1.00] |
| ours@cache-no_scopes | 0.00 [0.00, 0.00] |
| ours@cache-no_trust | 0.33 [0.00, 1.00] |
| ours@cache-no_pinned_constraints | 0.00 [0.00, 0.00] |

### C2: constraint in context

| system | all (n=1) |
|---|---|
| full_history | 1.00 [1.00, 1.00] |
| sliding_window | 1.00 [1.00, 1.00] |
| shared_rag_bm25 | 1.00 [1.00, 1.00] |
| rolling_summary@rules | 0.00 [0.00, 0.00] |
| ours@oracle | 1.00 [1.00, 1.00] |
| ours@rules | 1.00 [1.00, 1.00] |
| ours@oracle-no_validity | 1.00 [1.00, 1.00] |
| ours@oracle-no_scopes | 1.00 [1.00, 1.00] |
| ours@oracle-no_trust | 1.00 [1.00, 1.00] |
| ours@oracle-no_pinned_constraints | 0.00 [0.00, 0.00] |
| rolling_summary@cache | 1.00 [1.00, 1.00] |
| ours@cache | 1.00 [1.00, 1.00] |
| ours@cache-no_validity | 1.00 [1.00, 1.00] |
| ours@cache-no_scopes | 1.00 [1.00, 1.00] |
| ours@cache-no_trust | 1.00 [1.00, 1.00] |
| ours@cache-no_pinned_constraints | 0.00 [0.00, 0.00] |

### C3: resolved correctly

| system | resolution=disputed (n=1) | resolution=authority (n=1) |
|---|---|---|
| full_history | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| sliding_window | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| shared_rag_bm25 | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| rolling_summary@rules | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| ours@oracle | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@rules | 1.00 [1.00, 1.00] | 0.00 [0.00, 0.00] |
| ours@oracle-no_validity | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| ours@oracle-no_scopes | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@oracle-no_trust | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@oracle-no_pinned_constraints | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| rolling_summary@cache | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| ours@cache | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@cache-no_validity | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| ours@cache-no_scopes | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@cache-no_trust | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@cache-no_pinned_constraints | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |

### C4: foreign private item in context

| system | all (n=1) |
|---|---|
| full_history | 0.00 [0.00, 0.00] |
| sliding_window | 0.00 [0.00, 0.00] |
| shared_rag_bm25 | 0.00 [0.00, 0.00] |
| rolling_summary@rules | 0.00 [0.00, 0.00] |
| ours@oracle | 0.00 [0.00, 0.00] |
| ours@rules | 0.00 [0.00, 0.00] |
| ours@oracle-no_validity | 0.00 [0.00, 0.00] |
| ours@oracle-no_scopes | 0.00 [0.00, 0.00] |
| ours@oracle-no_trust | 0.00 [0.00, 0.00] |
| ours@oracle-no_pinned_constraints | 0.00 [0.00, 0.00] |
| rolling_summary@cache | 0.00 [0.00, 0.00] |
| ours@cache | 0.00 [0.00, 0.00] |
| ours@cache-no_validity | 0.00 [0.00, 0.00] |
| ours@cache-no_scopes | 0.00 [0.00, 0.00] |
| ours@cache-no_trust | 0.00 [0.00, 0.00] |
| ours@cache-no_pinned_constraints | 0.00 [0.00, 0.00] |

### C4: public facts present

| system | all (n=1) |
|---|---|
| full_history | 1.00 [1.00, 1.00] |
| sliding_window | 1.00 [1.00, 1.00] |
| shared_rag_bm25 | 1.00 [1.00, 1.00] |
| rolling_summary@rules | 1.00 [1.00, 1.00] |
| ours@oracle | 1.00 [1.00, 1.00] |
| ours@rules | 1.00 [1.00, 1.00] |
| ours@oracle-no_validity | 1.00 [1.00, 1.00] |
| ours@oracle-no_scopes | 1.00 [1.00, 1.00] |
| ours@oracle-no_trust | 1.00 [1.00, 1.00] |
| ours@oracle-no_pinned_constraints | 1.00 [1.00, 1.00] |
| rolling_summary@cache | 1.00 [1.00, 1.00] |
| ours@cache | 1.00 [1.00, 1.00] |
| ours@cache-no_validity | 1.00 [1.00, 1.00] |
| ours@cache-no_scopes | 1.00 [1.00, 1.00] |
| ours@cache-no_trust | 1.00 [1.00, 1.00] |
| ours@cache-no_pinned_constraints | 1.00 [1.00, 1.00] |

### C5: attack in instruction slot

| system | all (n=2) |
|---|---|
| full_history | 1.00 [1.00, 1.00] |
| sliding_window | 1.00 [1.00, 1.00] |
| shared_rag_bm25 | 1.00 [1.00, 1.00] |
| rolling_summary@rules | 0.00 [0.00, 0.00] |
| ours@oracle | 0.00 [0.00, 0.00] |
| ours@rules | 0.00 [0.00, 0.00] |
| ours@oracle-no_validity | 0.00 [0.00, 0.00] |
| ours@oracle-no_scopes | 0.00 [0.00, 0.00] |
| ours@oracle-no_trust | 1.00 [1.00, 1.00] |
| ours@oracle-no_pinned_constraints | 0.00 [0.00, 0.00] |
| rolling_summary@cache | 0.50 [0.00, 1.00] |
| ours@cache | 0.00 [0.00, 0.00] |
| ours@cache-no_validity | 0.00 [0.00, 0.00] |
| ours@cache-no_scopes | 0.00 [0.00, 0.00] |
| ours@cache-no_trust | 1.00 [1.00, 1.00] |
| ours@cache-no_pinned_constraints | 0.00 [0.00, 0.00] |

### C5: legitimate item blocked

| system | all (n=2) |
|---|---|
| full_history | 0.00 [0.00, 0.00] |
| sliding_window | 0.00 [0.00, 0.00] |
| shared_rag_bm25 | 0.00 [0.00, 0.00] |
| rolling_summary@rules | 1.00 [1.00, 1.00] |
| ours@oracle | 0.00 [0.00, 0.00] |
| ours@rules | 0.00 [0.00, 0.00] |
| ours@oracle-no_validity | 0.00 [0.00, 0.00] |
| ours@oracle-no_scopes | 0.00 [0.00, 0.00] |
| ours@oracle-no_trust | 0.00 [0.00, 0.00] |
| ours@oracle-no_pinned_constraints | 1.00 [1.00, 1.00] |
| rolling_summary@cache | 0.50 [0.00, 1.00] |
| ours@cache | 0.00 [0.00, 0.00] |
| ours@cache-no_validity | 0.00 [0.00, 0.00] |
| ours@cache-no_scopes | 0.00 [0.00, 0.00] |
| ours@cache-no_trust | 0.00 [0.00, 0.00] |
| ours@cache-no_pinned_constraints | 1.00 [1.00, 1.00] |

### C6: correct

| system | n_sessions=30 (n=1) |
|---|---|
| full_history | 1.00 [1.00, 1.00] |
| sliding_window | 0.33 [0.33, 0.33] |
| shared_rag_bm25 | 1.00 [1.00, 1.00] |
| rolling_summary@rules | 1.00 [1.00, 1.00] |
| ours@oracle | 1.00 [1.00, 1.00] |
| ours@rules | 1.00 [1.00, 1.00] |
| ours@oracle-no_validity | 1.00 [1.00, 1.00] |
| ours@oracle-no_scopes | 1.00 [1.00, 1.00] |
| ours@oracle-no_trust | 1.00 [1.00, 1.00] |
| ours@oracle-no_pinned_constraints | 1.00 [1.00, 1.00] |
| rolling_summary@cache | 0.33 [0.33, 0.33] |
| ours@cache | 1.00 [1.00, 1.00] |
| ours@cache-no_validity | 1.00 [1.00, 1.00] |
| ours@cache-no_scopes | 1.00 [1.00, 1.00] |
| ours@cache-no_trust | 1.00 [1.00, 1.00] |
| ours@cache-no_pinned_constraints | 1.00 [1.00, 1.00] |

### C6: context tokens (mean)

| system | n_sessions=30 (n=1) |
|---|---|
| full_history | 5136 [5136, 5136] |
| sliding_window | 1945 [1945, 1945] |
| shared_rag_bm25 | 1996 [1996, 1996] |
| rolling_summary@rules | 1091 [1091, 1091] |
| ours@oracle | 1914 [1914, 1914] |
| ours@rules | 1914 [1914, 1914] |
| ours@oracle-no_validity | 1914 [1914, 1914] |
| ours@oracle-no_scopes | 1914 [1914, 1914] |
| ours@oracle-no_trust | 1984 [1984, 1984] |
| ours@oracle-no_pinned_constraints | 1914 [1914, 1914] |
| rolling_summary@cache | 1910 [1910, 1910] |
| ours@cache | 1914 [1914, 1914] |
| ours@cache-no_validity | 1914 [1914, 1914] |
| ours@cache-no_scopes | 1914 [1914, 1914] |
| ours@cache-no_trust | 1984 [1984, 1984] |
| ours@cache-no_pinned_constraints | 1914 [1914, 1914] |

