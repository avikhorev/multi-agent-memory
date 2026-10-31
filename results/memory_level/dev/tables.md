# dev, memory level

### C0: correct

| system | all (n=20) |
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

### C1: current value present

| system | variant=explicit (n=7) | variant=implicit (n=13) |
|---|---|---|
| full_history | 1.00 [1.00, 1.00] | 0.00 [0.00, 0.00] |
| sliding_window | 1.00 [1.00, 1.00] | 0.00 [0.00, 0.00] |
| shared_rag_bm25 | 1.00 [1.00, 1.00] | 0.00 [0.00, 0.00] |
| rolling_summary@rules | 0.86 [0.57, 1.00] | 0.00 [0.00, 0.00] |
| ours@oracle | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@rules | 0.86 [0.57, 1.00] | 0.00 [0.00, 0.00] |
| ours@oracle-no_validity | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@oracle-no_scopes | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@oracle-no_trust | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@oracle-no_pinned_constraints | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |

### C1: stale value shown

| system | variant=explicit (n=7) | variant=implicit (n=13) |
|---|---|---|
| full_history | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| sliding_window | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| shared_rag_bm25 | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| rolling_summary@rules | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@oracle | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| ours@rules | 0.14 [0.00, 0.43] | 1.00 [1.00, 1.00] |
| ours@oracle-no_validity | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@oracle-no_scopes | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| ours@oracle-no_trust | 0.43 [0.14, 0.71] | 0.38 [0.15, 0.69] |
| ours@oracle-no_pinned_constraints | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |

### C2: constraint in context

| system | all (n=20) |
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

### C3: resolved correctly

| system | resolution=disputed (n=4) | resolution=authority (n=4) | resolution=later_event (n=12) |
|---|---|---|---|
| full_history | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.08 [0.00, 0.25] |
| sliding_window | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.08 [0.00, 0.25] |
| shared_rag_bm25 | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.08 [0.00, 0.25] |
| rolling_summary@rules | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.08 [0.00, 0.25] |
| ours@oracle | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@rules | 0.50 [0.00, 1.00] | 0.25 [0.00, 0.75] | 0.42 [0.17, 0.67] |
| ours@oracle-no_validity | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| ours@oracle-no_scopes | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@oracle-no_trust | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@oracle-no_pinned_constraints | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |

### C4: foreign private item in context

| system | all (n=20) |
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

### C4: public facts present

| system | all (n=20) |
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

### C5: attack in instruction slot

| system | all (n=20) |
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

### C5: legitimate item blocked

| system | all (n=20) |
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

### C6: correct

| system | n_sessions=10 (n=7) | n_sessions=20 (n=7) | n_sessions=30 (n=7) |
|---|---|---|---|
| full_history | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| sliding_window | 1.00 [1.00, 1.00] | 0.33 [0.33, 0.33] | 0.33 [0.33, 0.33] |
| shared_rag_bm25 | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| rolling_summary@rules | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@oracle | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@rules | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@oracle-no_validity | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@oracle-no_scopes | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@oracle-no_trust | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@oracle-no_pinned_constraints | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |

### C6: context tokens (mean)

| system | n_sessions=10 (n=7) | n_sessions=20 (n=7) | n_sessions=30 (n=7) |
|---|---|---|---|
| full_history | 1607 [1457, 1774] | 3777 [3644, 3912] | 5430 [5330, 5533] |
| sliding_window | 1592 [1456, 1740] | 1952 [1936, 1967] | 1959 [1951, 1968] |
| shared_rag_bm25 | 1594 [1456, 1745] | 1988 [1984, 1992] | 1990 [1987, 1992] |
| rolling_summary@rules | 295 [283, 309] | 709 [673, 738] | 1096 [1074, 1118] |
| ours@oracle | 631 [519, 749] | 1521 [1426, 1674] | 1972 [1920, 1999] |
| ours@rules | 631 [519, 749] | 1521 [1426, 1674] | 1972 [1920, 1999] |
| ours@oracle-no_validity | 631 [519, 749] | 1521 [1426, 1674] | 1972 [1920, 1999] |
| ours@oracle-no_scopes | 631 [519, 749] | 1521 [1426, 1674] | 1972 [1920, 1999] |
| ours@oracle-no_trust | 884 [724, 1038] | 1942 [1897, 1977] | 1991 [1988, 1995] |
| ours@oracle-no_pinned_constraints | 631 [519, 749] | 1521 [1426, 1674] | 1972 [1920, 1999] |

