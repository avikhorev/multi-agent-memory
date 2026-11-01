# ours4: criteria of D40

Paraphrased C2 scenarios where rule_constraints does not fire (main set): 6 of 6: C2-eval-0006, C2-eval-0007, C2-eval-0008, C2-eval-0009, C2-eval-0010, C2-eval-0011

| system | constraint checks ok, all C2 (of 6) | corrected (no update_record) | update_record at constraint checks | main set corrected | injection checks ok | all C5 checks ok |
|---|---|---|---|---|---|---|
| ours | 6/6 | 0/6 | 6 | 0/6 | 3/3 | 11/12 |
| ours3 | 6/6 | 6/6 | 0 | 6/6 | 3/3 | 12/12 |
| ours4 | 6/6 | 6/6 | 0 | 6/6 | 3/3 | 10/12 |

Set B (ours4 on the 21 fresh scenarios): all checks ok 73/78 (ours3 on the same scenarios: 70/78); Reviewer rejected 49/240.
Pinned constraints of ours4 over 30 units: matching the scenario constraints 9, false 40 (per unit 1.33), from untrusted records 0; main-set scenarios with the rule pinned: 6 of 6; C2 scenarios where the rule fires (shown separately): 0, pinned in 0.

Verdict: partial.
ours3 has the same number of corrected constraint checks as ours4 on the main set of A: no gain in the live checks is shown, the difference is the pinning only.
