# Hand classification of the answers with prefix (the labeller is the agent)

| system | current | stale | both | absent |
|---|---|---|---|---|
| full_history_meta | 6 | 2 | 3 | 1 |
| sliding_window_meta | 6 | 3 | 2 | 1 |
| shared_rag_bm25_meta | 9 | 2 | 1 | 0 |
| rolling_summary_meta | 2 | 4 | 6 | 0 |

| id | system | scenario | repeat | strict | class | answer |
|---|---|---|---|---|---|---|
| p32 | full_history_meta | C1-eval-0000 | 0 | fail | current | The search module contingency reserve is currently USD 153,000, updated from USD 727,000. |
| p01 | full_history_meta | C1-eval-0000 | 1 | fail | current | The current contingency reserve for the search module is USD 153,000, updated in session 6 from USD 727,000. |
| p43 | full_history_meta | C1-eval-0001 | 0 | pass | current | The current migration module pilot user count is 104,250. |
| p44 | full_history_meta | C1-eval-0001 | 1 | pass | current | Current migration pilot user count is 104,250. |
| p10 | full_history_meta | C1-eval-0002 | 0 | fail | current | Likely 2026-06-15: 2026-06-27 less 12 days; sponsor confirmation needed. |
| p47 | full_history_meta | C1-eval-0002 | 1 | fail | stale | Recorded: 2026-06-27; pending user confirmation of 2026-06-15. |
| p11 | full_history_meta | C3-eval-0000 | 0 | fail | both | The admin module sign-off date is unresolved. Memory has two conflicting dates: 2026-05-19 (status feed, 2026-01-27) and 2026-07-19 (vendor document, 2026-02-10). |
| p46 | full_history_meta | C3-eval-0000 | 1 | fail | both | Admin sign-off date unverified: memory shows 2026-05-19 and 2026-07-19. |
| p38 | full_history_meta | C3-eval-0001 | 0 | pass | current | Recorded as 2026-04-23 per vendor document, as of 2026-01-19. |
| p37 | full_history_meta | C3-eval-0001 | 1 | fail | both | Records conflict: 2026-04-23 (vendor doc) vs about 2026-08-14. |
| p20 | full_history_meta | C3-eval-0002 | 0 | fail | absent | Sign-off date conflicts in memory; not confirmed. Verify status feed. |
| p31 | full_history_meta | C3-eval-0002 | 1 | fail | stale | Sign-off date for notifications module: 2026-07-17 per vendor document (as of 2026-01-24). |
| p28 | rolling_summary_meta | C1-eval-0000 | 0 | fail | both | Unverified: D-051 says USD 727,000; session 6 says USD 153,000. |
| p04 | rolling_summary_meta | C1-eval-0000 | 1 | fail | both | Unverified: D-051 shows USD 727,000; session 6 update says USD 153,000. |
| p41 | rolling_summary_meta | C1-eval-0001 | 0 | fail | stale | No verified figure. Reported 69,500 (session 4) lacks a source record. |
| p29 | rolling_summary_meta | C1-eval-0001 | 1 | fail | stale | Migration module pilot user count is 69,500, from session 4 status update; unverified, so not confirmed as current. |
| p05 | rolling_summary_meta | C1-eval-0002 | 0 | fail | stale | No verified current date; last recorded 2026-06-27 is unverified and stale. |
| p40 | rolling_summary_meta | C1-eval-0002 | 1 | fail | stale | The migration module handover date is 2026-06-27, user-stated in sessions 1–4. It precedes today and is unconfirmed; the session 6 12-day slip has no verified base date, so no revised date is recorded. |
| p07 | rolling_summary_meta | C3-eval-0000 | 0 | fail | both | Admin module sign-off date is unconfirmed. Sources conflict: 2026-06-22, 2026-05-19, and 2026-07-19. Admin UAT starts 2026-11-12. |
| p16 | rolling_summary_meta | C3-eval-0000 | 1 | fail | both | The admin module sign-off date is unresolved. Memory records two conflicting dates: 2026-05-19 (status feed, as of 2026-01-27) and 2026-07-19 (vendor document, as of 2026-02-10). Neither is verified; reconcile before use. |
| p21 | rolling_summary_meta | C3-eval-0001 | 0 | pass | current | Search module sign-off date: 2026-04-23, per vendor document dated 2026-01-19. |
| p39 | rolling_summary_meta | C3-eval-0001 | 1 | pass | current | The search module sign-off date is 2026-04-23, per a vendor document dated 2026-01-19. Note that it conflicts with the user-supplied handover and UAT dates. |
| p12 | rolling_summary_meta | C3-eval-0002 | 0 | fail | both | Not confirmed. Memory gives two conflicting dates: 2026-07-17 (vendor document dated 2026-01-24) and four weeks after UAT start (UAT start 2026-09-28, unverified). Both conflict with today's date. Confirm with the project owner before recording. |
| p18 | rolling_summary_meta | C3-eval-0002 | 1 | fail | both | Unconfirmed; sources conflict: ~2026-10-26 (status feed) vs 2026-07-17 (vendor). |
| p14 | shared_rag_bm25_meta | C1-eval-0000 | 0 | pass | current | The current contingency reserve for the search module is USD 153,000. |
| p45 | shared_rag_bm25_meta | C1-eval-0000 | 1 | fail | current | The search module's contingency reserve is USD 153,000, updated in session 6, replacing USD 727,000 in D-051. |
| p22 | shared_rag_bm25_meta | C1-eval-0001 | 0 | fail | current | The migration module pilot user count is 104,250, derived from 69,500 growing by half. |
| p15 | shared_rag_bm25_meta | C1-eval-0001 | 1 | fail | current | Implied 104,250: recorded 69,500 grown by half; base unconfirmed. |
| p36 | shared_rag_bm25_meta | C1-eval-0002 | 0 | pass | current | Likely 2026-06-15, pulled in 12 days; sponsor confirmation pending. |
| p25 | shared_rag_bm25_meta | C1-eval-0002 | 1 | fail | current | Likely 2026-06-15: recorded 2026-06-27, pulled in 12 days. Unconfirmed and stale. |
| p08 | shared_rag_bm25_meta | C3-eval-0000 | 0 | fail | current | Likely 2026-07-19 (vendor doc, 2026-02-10); conflicts with 2026-05-19. |
| p35 | shared_rag_bm25_meta | C3-eval-0000 | 1 | fail | both | Sign-off date conflicts: 2026-07-19 (vendor) vs 2026-05-19 (status feed). |
| p02 | shared_rag_bm25_meta | C3-eval-0001 | 0 | pass | current | 2026-04-23 per planner note; conflicts with worker note. |
| p24 | shared_rag_bm25_meta | C3-eval-0001 | 1 | pass | current | Search sign-off: 2026-04-23 (vendor doc, 2026-01-19); unconfirmed. |
| p30 | shared_rag_bm25_meta | C3-eval-0002 | 0 | fail | stale | Sign-off date recorded as 2026-07-17 (vendor document, as of 2026-01-24). |
| p26 | shared_rag_bm25_meta | C3-eval-0002 | 1 | fail | stale | 2026-07-17, per vendor document recorded 2026-01-24. |
| p17 | sliding_window_meta | C1-eval-0000 | 0 | fail | current | USD 153,000, updated in session 6 from USD 727,000. |
| p33 | sliding_window_meta | C1-eval-0000 | 1 | fail | current | USD 153,000, updated from USD 727,000 per the session 6 user update. |
| p23 | sliding_window_meta | C1-eval-0001 | 0 | fail | current | Migration pilot user count is 104,250 (69,500 plus half). |
| p09 | sliding_window_meta | C1-eval-0001 | 1 | fail | stale | Last confirmed: 69,500. Session 5 growth by half is unconfirmed. |
| p03 | sliding_window_meta | C1-eval-0002 | 0 | fail | absent | No handover date is on record for the migration module. |
| p27 | sliding_window_meta | C1-eval-0002 | 1 | fail | current | Current migration handover is 2026-06-15, derived from 2026-06-27 pulled in 12 days; unconfirmed. |
| p13 | sliding_window_meta | C3-eval-0000 | 0 | fail | both | Admin sign-off date conflicts: 2026-05-19 or 2026-07-19; unverified. |
| p42 | sliding_window_meta | C3-eval-0000 | 1 | fail | both | Admin sign-off date is conflicting: 2026-05-19 or 2026-07-19. Unresolved; needs verification. |
| p06 | sliding_window_meta | C3-eval-0001 | 0 | pass | current | 2026-04-23, per vendor document dated 2026-01-19; not yet user-confirmed. |
| p19 | sliding_window_meta | C3-eval-0001 | 1 | pass | current | 2026-04-23 per vendor document; pending user confirmation. |
| p34 | sliding_window_meta | C3-eval-0002 | 0 | fail | stale | The sign-off date for the notifications module is 2026-07-17, per the vendor document dated 2026-01-24. This is a planner note, not a verified source document. |
| p48 | sliding_window_meta | C3-eval-0002 | 1 | fail | stale | Memory gives 2026-07-17, citing a vendor document; not verified this session. |
