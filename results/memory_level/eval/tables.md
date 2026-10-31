# eval, memory level

### C0: correct

| system | all (n=30) |
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

### C1: current value present

| system | variant=explicit (n=10) | variant=implicit (n=20) |
|---|---|---|
| full_history | 1.00 [1.00, 1.00] | 0.10 [0.00, 0.25] |
| sliding_window | 1.00 [1.00, 1.00] | 0.10 [0.00, 0.25] |
| shared_rag_bm25 | 1.00 [1.00, 1.00] | 0.10 [0.00, 0.25] |
| rolling_summary@rules | 0.90 [0.70, 1.00] | 0.10 [0.00, 0.25] |
| ours@oracle | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@rules | 0.90 [0.70, 1.00] | 0.10 [0.00, 0.25] |
| ours@oracle-no_validity | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@oracle-no_scopes | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@oracle-no_trust | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@oracle-no_pinned_constraints | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| rolling_summary@cache | 1.00 [1.00, 1.00] | 0.60 [0.40, 0.80] |
| ours@cache | 1.00 [1.00, 1.00] | 0.95 [0.85, 1.00] |
| ours@cache-no_validity | 1.00 [1.00, 1.00] | 0.95 [0.85, 1.00] |
| ours@cache-no_scopes | 1.00 [1.00, 1.00] | 0.95 [0.85, 1.00] |
| ours@cache-no_trust | 1.00 [1.00, 1.00] | 0.95 [0.85, 1.00] |
| ours@cache-no_pinned_constraints | 1.00 [1.00, 1.00] | 0.95 [0.85, 1.00] |

### C1: stale value shown

| system | variant=explicit (n=10) | variant=implicit (n=20) |
|---|---|---|
| full_history | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| sliding_window | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| shared_rag_bm25 | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| rolling_summary@rules | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@oracle | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| ours@rules | 0.10 [0.00, 0.30] | 1.00 [1.00, 1.00] |
| ours@oracle-no_validity | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@oracle-no_scopes | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| ours@oracle-no_trust | 0.30 [0.00, 0.60] | 0.20 [0.05, 0.40] |
| ours@oracle-no_pinned_constraints | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| rolling_summary@cache | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@cache | 0.00 [0.00, 0.00] | 0.05 [0.00, 0.15] |
| ours@cache-no_validity | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@cache-no_scopes | 0.00 [0.00, 0.00] | 0.05 [0.00, 0.15] |
| ours@cache-no_trust | 0.30 [0.00, 0.60] | 0.25 [0.10, 0.45] |
| ours@cache-no_pinned_constraints | 0.00 [0.00, 0.00] | 0.05 [0.00, 0.15] |

### C2: constraint in context

| system | all (n=30) |
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

| system | resolution=disputed (n=6) | resolution=authority (n=6) | resolution=later_event (n=18) |
|---|---|---|---|
| full_history | 0.00 [0.00, 0.00] | 0.17 [0.00, 0.50] | 0.50 [0.28, 0.72] |
| sliding_window | 0.00 [0.00, 0.00] | 0.17 [0.00, 0.50] | 0.50 [0.28, 0.72] |
| shared_rag_bm25 | 0.00 [0.00, 0.00] | 0.17 [0.00, 0.50] | 0.50 [0.28, 0.72] |
| rolling_summary@rules | 0.00 [0.00, 0.00] | 0.17 [0.00, 0.50] | 0.50 [0.28, 0.72] |
| ours@oracle | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@rules | 0.33 [0.00, 0.67] | 0.50 [0.17, 0.83] | 0.83 [0.67, 1.00] |
| ours@oracle-no_validity | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| ours@oracle-no_scopes | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@oracle-no_trust | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@oracle-no_pinned_constraints | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| rolling_summary@cache | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.28 [0.11, 0.50] |
| ours@cache | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@cache-no_validity | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| ours@cache-no_scopes | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@cache-no_trust | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@cache-no_pinned_constraints | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |

### C4: foreign private item in context

| system | all (n=30) |
|---|---|
| full_history | 0.00 [0.00, 0.00] |
| sliding_window | 0.00 [0.00, 0.00] |
| shared_rag_bm25 | 0.00 [0.00, 0.00] |
| rolling_summary@rules | 0.00 [0.00, 0.00] |
| ours@oracle | 0.00 [0.00, 0.00] |
| ours@rules | 0.00 [0.00, 0.00] |
| ours@oracle-no_validity | 0.00 [0.00, 0.00] |
| ours@oracle-no_scopes | 0.50 [0.33, 0.70] |
| ours@oracle-no_trust | 0.00 [0.00, 0.00] |
| ours@oracle-no_pinned_constraints | 0.00 [0.00, 0.00] |
| rolling_summary@cache | 0.00 [0.00, 0.00] |
| ours@cache | 0.00 [0.00, 0.00] |
| ours@cache-no_validity | 0.00 [0.00, 0.00] |
| ours@cache-no_scopes | 0.00 [0.00, 0.00] |
| ours@cache-no_trust | 0.00 [0.00, 0.00] |
| ours@cache-no_pinned_constraints | 0.00 [0.00, 0.00] |

### C4: public facts present

| system | all (n=30) |
|---|---|
| full_history | 1.00 [1.00, 1.00] |
| sliding_window | 1.00 [1.00, 1.00] |
| shared_rag_bm25 | 1.00 [1.00, 1.00] |
| rolling_summary@rules | 1.00 [1.00, 1.00] |
| ours@oracle | 1.00 [1.00, 1.00] |
| ours@rules | 1.00 [1.00, 1.00] |
| ours@oracle-no_validity | 1.00 [1.00, 1.00] |
| ours@oracle-no_scopes | 0.53 [0.37, 0.70] |
| ours@oracle-no_trust | 1.00 [1.00, 1.00] |
| ours@oracle-no_pinned_constraints | 1.00 [1.00, 1.00] |
| rolling_summary@cache | 1.00 [1.00, 1.00] |
| ours@cache | 1.00 [1.00, 1.00] |
| ours@cache-no_validity | 1.00 [1.00, 1.00] |
| ours@cache-no_scopes | 1.00 [1.00, 1.00] |
| ours@cache-no_trust | 1.00 [1.00, 1.00] |
| ours@cache-no_pinned_constraints | 1.00 [1.00, 1.00] |

### C5: attack in instruction slot

| system | all (n=30) |
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
| rolling_summary@cache | 0.23 [0.10, 0.40] |
| ours@cache | 0.00 [0.00, 0.00] |
| ours@cache-no_validity | 0.00 [0.00, 0.00] |
| ours@cache-no_scopes | 0.00 [0.00, 0.00] |
| ours@cache-no_trust | 1.00 [1.00, 1.00] |
| ours@cache-no_pinned_constraints | 0.00 [0.00, 0.00] |

### C5: legitimate item blocked

| system | all (n=30) |
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
| rolling_summary@cache | 0.00 [0.00, 0.00] |
| ours@cache | 0.00 [0.00, 0.00] |
| ours@cache-no_validity | 0.00 [0.00, 0.00] |
| ours@cache-no_scopes | 0.00 [0.00, 0.00] |
| ours@cache-no_trust | 0.00 [0.00, 0.00] |
| ours@cache-no_pinned_constraints | 1.00 [1.00, 1.00] |

### C6: correct

| system | n_sessions=10 (n=10) | n_sessions=20 (n=10) | n_sessions=30 (n=10) |
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
| rolling_summary@cache | 1.00 [1.00, 1.00] | 0.77 [0.57, 0.93] | 0.53 [0.33, 0.73] |
| ours@cache | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@cache-no_validity | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@cache-no_scopes | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@cache-no_trust | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| ours@cache-no_pinned_constraints | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |

### C6: context tokens (mean)

| system | n_sessions=10 (n=10) | n_sessions=20 (n=10) | n_sessions=30 (n=10) |
|---|---|---|---|
| full_history | 1610 [1506, 1702] | 3508 [3404, 3609] | 5609 [5369, 5836] |
| sliding_window | 1607 [1506, 1696] | 1961 [1953, 1971] | 1956 [1946, 1965] |
| shared_rag_bm25 | 1608 [1506, 1697] | 1989 [1987, 1991] | 1991 [1988, 1994] |
| rolling_summary@rules | 320 [307, 328] | 685 [663, 704] | 1100 [1080, 1121] |
| ours@oracle | 627 [519, 730] | 1383 [1302, 1463] | 1984 [1970, 1997] |
| ours@rules | 627 [519, 730] | 1383 [1302, 1463] | 1984 [1970, 1997] |
| ours@oracle-no_validity | 627 [519, 730] | 1383 [1302, 1463] | 1984 [1970, 1997] |
| ours@oracle-no_scopes | 627 [519, 730] | 1383 [1302, 1463] | 1984 [1970, 1997] |
| ours@oracle-no_trust | 720 [585, 847] | 1590 [1488, 1694] | 1989 [1987, 1992] |
| ours@oracle-no_pinned_constraints | 627 [519, 730] | 1383 [1302, 1463] | 1984 [1970, 1997] |
| rolling_summary@cache | 969 [847, 1086] | 1755 [1484, 1934] | 1954 [1926, 1977] |
| ours@cache | 627 [519, 730] | 1385 [1303, 1465] | 1986 [1972, 1998] |
| ours@cache-no_validity | 627 [519, 730] | 1385 [1303, 1465] | 1986 [1972, 1998] |
| ours@cache-no_scopes | 627 [519, 730] | 1385 [1303, 1465] | 1986 [1972, 1998] |
| ours@cache-no_trust | 720 [585, 847] | 1592 [1489, 1696] | 1989 [1987, 1991] |
| ours@cache-no_pinned_constraints | 627 [519, 730] | 1385 [1303, 1465] | 1986 [1972, 1998] |

