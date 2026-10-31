| system | current | stale | both | absent |
|---|---|---|---|---|
| full_history | 3 | 3 | 6 | 0 |
| ours | 12 | 0 | 0 | 0 |
| rolling_summary | 5 | 2 | 5 | 0 |
| shared_rag_bm25 | 3 | 3 | 6 | 0 |
| sliding_window | 2 | 4 | 5 | 1 |

# Hand classification of the C1/C3 factor answers (author's judgement)

Classes: current = asserts the current value; stale = asserts the stale value; both = names both without deciding; absent = no value.

| id | system | scenario | repeat | strict | class | answer |
|---|---|---|---|---|---|---|
| b14 | full_history | C1-eval-0000 | 0 | fail | stale | USD 727,000 per D-051; the 153,000 change is unverified. |
| b31 | full_history | C1-eval-0000 | 1 | fail | current | The current search module contingency reserve is USD 153,000, updated from USD 727,000. |
| b53 | full_history | C1-eval-0001 | 0 | fail | stale | Recorded pilot user count is 69,500; growth by half unconfirmed. |
| b17 | full_history | C1-eval-0001 | 1 | fail | stale | Migration module pilot user count is 69,500 per memory. |
| b55 | full_history | C1-eval-0002 | 0 | fail | current | Unconfirmed: 2026-06-27 minus 12 days, about 2026-06-15; past. |
| b40 | full_history | C1-eval-0002 | 1 | fail | current | 2026-06-15, derived from 2026-06-27 pulled in 12 days. |
| b46 | full_history | C3-eval-0000 | 0 | fail | both | The admin module sign-off date is unconfirmed. Sources conflict: 2026-05-19 (status feed, as of 2026-01-27) and 2026-07-19 (vendor document, as of 2026-02-10). |
| b02 | full_history | C3-eval-0000 | 1 | fail | both | Sources conflict: 2026-05-19 or 2026-07-19; unconfirmed. |
| b16 | full_history | C3-eval-0001 | 0 | fail | both | Conflicting records: 2026-04-23 (vendor, 2026-01-19) vs ~2026-08-14. |
| b05 | full_history | C3-eval-0001 | 1 | fail | both | Unconfirmed: 2026-04-23 (vendor, 2026-01-19) conflicts with ~2026-08-14. |
| b47 | full_history | C3-eval-0002 | 0 | fail | both | Sign-off date is unconfirmed. Memory gives 2026-07-17 (vendor document) and 2026-10-26 (UAT start plus four weeks). Verify before reporting. |
| b36 | full_history | C3-eval-0002 | 1 | fail | both | Conflicting: 2026-07-17 (vendor doc) vs 2026-10-26 (UAT+4 weeks). Verify source. |
| b21 | ours | C1-eval-0000 | 0 | pass | current | The current contingency reserve for the search module is 153000 USD. |
| b52 | ours | C1-eval-0000 | 1 | pass | current | The current contingency reserve for the Atlas/search module is 153000 USD. |
| b49 | ours | C1-eval-0001 | 0 | pass | current | The migration module's recorded user count is 104250. |
| b59 | ours | C1-eval-0001 | 1 | pass | current | Atlas/migration user_count is 104250. |
| b08 | ours | C1-eval-0002 | 0 | pass | current | The current handover date for the migration module is 2026-06-15. |
| b42 | ours | C1-eval-0002 | 1 | pass | current | The current handover date for the migration module is 2026-06-15. |
| b10 | ours | C3-eval-0000 | 0 | pass | current | The sign-off date for the admin module is 2026-07-19. |
| b60 | ours | C3-eval-0000 | 1 | pass | current | The sign-off date for the admin module is 2026-07-19. |
| b28 | ours | C3-eval-0001 | 0 | pass | current | The sign-off date for Atlas/search is 2026-04-23. |
| b20 | ours | C3-eval-0001 | 1 | pass | current | The sign-off date for Atlas/search is 2026-04-23. |
| b03 | ours | C3-eval-0002 | 0 | pass | current | The sign-off date for the Atlas/notifications module is 2026-10-26. |
| b34 | ours | C3-eval-0002 | 1 | pass | current | The sign-off date for the Atlas/notifications module is 2026-10-26. |
| b56 | rolling_summary | C1-eval-0000 | 0 | fail | current | Unverified: reported USD 153,000, down from USD 727,000; confirm with sponsor. |
| b06 | rolling_summary | C1-eval-0000 | 1 | fail | current | The search module contingency reserve is USD 153,000 per the latest update. It replaces the previously recorded USD 727,000 from D-051, which is unverified. A source record for the new value has been requested. |
| b04 | rolling_summary | C1-eval-0001 | 0 | fail | stale | 69,500 (user-reported; no D-021 record; unverified). |
| b19 | rolling_summary | C1-eval-0001 | 1 | fail | stale | Migration module pilot user count is 69,500, but it is unsourced and unverified. Source record needed before accepting. |
| b07 | rolling_summary | C1-eval-0002 | 0 | fail | both | Unconfirmed: previously 2026-06-27; user implies 2026-06-15. |
| b27 | rolling_summary | C1-eval-0002 | 1 | fail | current | Migration handover date: 2026-06-15 per latest tool note, unverified. Earlier note said 2026-06-27. Project record verification required. |
| b50 | rolling_summary | C3-eval-0000 | 0 | fail | both | Unresolved: sources conflict. Candidates: 2026-05-19, 2026-06-22, 2026-07-19. |
| b13 | rolling_summary | C3-eval-0000 | 1 | fail | both | Two conflicting dates: 2026-05-19 and 2026-07-19. Confirm with sponsor. |
| b54 | rolling_summary | C3-eval-0001 | 0 | pass | current | 2026-04-23, per vendor document dated 2026-01-19; not independently verified. |
| b01 | rolling_summary | C3-eval-0001 | 1 | pass | current | Search module sign-off date is unverified: vendor document dated 2026-01-19 says 2026-04-23, which conflicts with the 2026-04-29 handover date. Confirm against project records. |
| b09 | rolling_summary | C3-eval-0002 | 0 | fail | both | Unconfirmed: sources conflict, 2026-10-26 vs 2026-07-17. Confirm before reporting. |
| b22 | rolling_summary | C3-eval-0002 | 1 | fail | both | Not confirmed. Conflicting dates: about 2026-10-26 (status feed) vs 2026-07-17 (vendor document). |
| b45 | shared_rag_bm25 | C1-eval-0000 | 0 | fail | stale | USD 727,000 recorded; change to 153,000 awaits sponsor confirmation. |
| b44 | shared_rag_bm25 | C1-eval-0000 | 1 | fail | current | USD 153,000 per latest update; conflicts with D-051's USD 727,000. |
| b23 | shared_rag_bm25 | C1-eval-0001 | 0 | fail | current | Current migration pilot user count is 104,250: 69,500 grown by half. |
| b29 | shared_rag_bm25 | C1-eval-0001 | 1 | fail | stale | The recorded pilot user count for the migration module is 69,500. |
| b48 | shared_rag_bm25 | C1-eval-0002 | 0 | fail | stale | Recorded handover date is 2026-06-27; 2026-06-15 is pending sponsor verification. |
| b25 | shared_rag_bm25 | C1-eval-0002 | 1 | fail | current | Likely 2026-06-15: prior 2026-06-27 pulled in 12 days. |
| b15 | shared_rag_bm25 | C3-eval-0000 | 0 | fail | both | Conflicting: 2026-07-19 (vendor doc) vs 2026-05-19 (status feed); verify. |
| b12 | shared_rag_bm25 | C3-eval-0000 | 1 | fail | both | Conflicting records: 2026-07-19 (vendor doc, 2026-02-10) vs 2026-05-19 (status feed, 2026-01-27). |
| b38 | shared_rag_bm25 | C3-eval-0001 | 0 | fail | both | Sign-off date conflicts: 2026-04-23 or about 2026-08-14; confirm with user. |
| b32 | shared_rag_bm25 | C3-eval-0001 | 1 | fail | both | Memory conflicts: 2026-04-23 (planner note) vs 2026-08-14 (worker note). |
| b57 | shared_rag_bm25 | C3-eval-0002 | 0 | fail | both | Conflict: 2026-07-17 per vendor document; 2026-10-26 per UAT-plus-four-weeks. |
| b39 | shared_rag_bm25 | C3-eval-0002 | 1 | fail | both | Conflicting: 2026-07-17 (vendor document) vs 2026-10-26 (UAT plus four weeks). |
| b58 | sliding_window | C1-eval-0000 | 0 | fail | current | USD 153,000 per the memory update; D-051 still shows USD 727,000. |
| b37 | sliding_window | C1-eval-0000 | 1 | fail | current | Unverified: memory notes USD 153,000, previously USD 727,000. |
| b33 | sliding_window | C1-eval-0001 | 0 | fail | stale | The recorded migration module pilot user count is 69,500. |
| b30 | sliding_window | C1-eval-0001 | 1 | fail | stale | Unconfirmed: 69,500 reported; sponsor verification still pending. |
| b43 | sliding_window | C1-eval-0002 | 0 | fail | stale | Migration module handover date is 2026-06-27 per memory. |
| b26 | sliding_window | C1-eval-0002 | 1 | fail | stale | Recorded handover is 2026-06-27; proposed 2026-06-15 awaits confirmation. |
| b11 | sliding_window | C3-eval-0000 | 0 | fail | both | Admin sign-off date unconfirmed: memory shows 2026-05-19 and 2026-07-19. |
| b35 | sliding_window | C3-eval-0000 | 1 | fail | both | Two conflicting sign-off dates exist for the admin module: 2026-05-19 and 2026-07-19. Neither is confirmed, so I cannot give a verified date. |
| b24 | sliding_window | C3-eval-0001 | 0 | fail | both | Unconfirmed: 2026-04-23 (vendor doc, 2026-01-19) vs about 2026-08-14 (worker note). |
| b41 | sliding_window | C3-eval-0001 | 1 | fail | both | Conflicting: 2026-04-23 (planner note) vs 2026-08-14 (worker note). |
| b51 | sliding_window | C3-eval-0002 | 0 | fail | both | Sources conflict: 2026-10-26 (UAT plus four weeks) vs 2026-07-17 (vendor document). |
| b18 | sliding_window | C3-eval-0002 | 1 | fail | absent | Conflicting sign-off dates in memory; cannot confirm. Verify logged value. |
