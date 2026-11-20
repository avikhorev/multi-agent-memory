# Decision index D1–D45

[`DECISIONS.md`](DECISIONS.md) is a **chronology that is unchanged in meaning**: it records what was known at each step. This index answers a different question: **what value does a decision have now?** It does not replace the original wording or the results.

Statuses: **active** — a rule or implementation is used now; **history** — a completed stage of the research or a measurement; **superseded** — an intermediate choice later refined; **problem** — a known unresolved defect or a significant limitation; **post hoc** — a separate work after the freeze, which must not be mixed with the main experiment. The status "post hoc" does not mean that the experiment is obsolete.

| Decision | Status | What matters now |
|---|---|---|
| [D1](DECISIONS.md#d1) | Active | Claude Code is pinned to 2.1.316 |
| [D2](DECISIONS.md#d2) | Active | The call flags and the thinking mode are fixed |
| [D3](DECISIONS.md#d3) | Active | The subprocess environment is filtered |
| [D4](DECISIONS.md#d4) | Active | The offline token counter is calibrated; not "characters / 4" |
| [D5](DECISIONS.md#d5) | Active | `refusal` is counted separately |
| [D6](DECISIONS.md#d6) | Active | The standard parallelism is 8; the budget carries a risk (see D44) |
| [D7](DECISIONS.md#d7) | Active | The `--bare` flag is not used |
| [D8](DECISIONS.md#d8) | History | A list of what had not been verified **at the time of the pilot** |
| [D9](DECISIONS.md#d9) | Superseded by D21 | In the pilot the choice of A/B was still open; A was chosen |
| [D10](DECISIONS.md#d10) | Active | The compact answer format of the roles |
| [D11](DECISIONS.md#d11) | History | How the generator and the acceptance tests were prepared |
| [D12](DECISIONS.md#d12) | Active | The actual structure of the original `ours` |
| [D13](DECISIONS.md#d13) | Problem | The generator's skew and the risk of tuning on `dev` |
| [D14](DECISIONS.md#d14) | Active | The live protocol and prompts after the smoke test |
| [D15](DECISIONS.md#d15) | History | Corrections of the skews on `dev`; `holdout` is not fully independent |
| [D16](DECISIONS.md#d16) | History | Mutation testing of the memory core |
| [D17](DECISIONS.md#d17) | Active | The rules of the freeze and the interpretation of the main comparison |
| [D18](DECISIONS.md#d18) | History | The trial extraction and the elimination of `null` |
| [D19](DECISIONS.md#d19) | Active | Cleaning of the service environment block in the summary |
| [D20](DECISIONS.md#d20) | Problem | The cost limit on resumption is not fixed |
| [D21](DECISIONS.md#d21) | Active | The main live run: variant A |
| [D22](DECISIONS.md#d22) | History | The result of the original live run |
| [D23](DECISIONS.md#d23) | Post hoc | Check of sensitivity and of the soft count of C1/C3 |
| [D24](DECISIONS.md#d24) | Post hoc | Additional controls of the sources of the gap |
| [D25](DECISIONS.md#d25) | Problem | Memory uses knowledge of the generator's patterns |
| [D26](DECISIONS.md#d26) | Active | New runs are written to `results/live/rerun` |
| [D27](DECISIONS.md#d27) | Post hoc | Plan for the check of the presentation of author and time |
| [D28](DECISIONS.md#d28) | Post hoc | Control repeat of the live layer |
| [D29](DECISIONS.md#d29) | Post hoc | Results of the change in presentation |
| [D30](DECISIONS.md#d30) | Post hoc | Plan of the `ours2` variant |
| [D31](DECISIONS.md#d31) | Post hoc | Result of the offline stage of `ours2` |
| [D32](DECISIONS.md#d32) | Post hoc | Plan of the live check of `ours2_lite` |
| [D33](DECISIONS.md#d33) | Post hoc | Results of `ours2` and `ours2_lite` |
| [D34](DECISIONS.md#d34) | Post hoc | Plan of the `ours3` variant |
| [D35](DECISIONS.md#d35) | Post hoc | Result of the offline stage of `ours3` |
| [D36](DECISIONS.md#d36) | Post hoc | Live `ours3` on the original scenarios |
| [D37](DECISIONS.md#d37) | Post hoc | Plan of the new scenarios and rephrasing |
| [D38](DECISIONS.md#d38) | Post hoc | `ours3` did not outperform `ours` on the new scenarios |
| [D39](DECISIONS.md#d39) | Problem | Defect of the evaluator; the adjusted count is post hoc only |
| [D40](DECISIONS.md#d40) | Post hoc | Plan of `ours4`, a deviation from the rule on stopping iterations |
| [D41](DECISIONS.md#d41) | Post hoc | Fixing of the `ours4` rules and false fixings |
| [D42](DECISIONS.md#d42) | Post hoc | Plan for Mem0, Graphiti, A-Mem; A-Mem was not run |
| [D43](DECISIONS.md#d43) | Post hoc | Reductions and limitations of the external adapters |
| [D44](DECISIONS.md#d44) | Post hoc | Results of the external comparison and the Graphiti limit overrun |
| [D45](DECISIONS.md#d45) | Problem | Gaps for production work; the plan is in PRODUCTION.md, not implemented |

## Quick links

- [Current run conditions](RUNBOOK.md) and [exact scenario rules](SCENARIO_FORMAT.md).
- [Known defects and limitations](KNOWN_ISSUES.md) — what is not yet fixed, what to re-check by hand.
- [Evidence for the numbers](EVIDENCE.md) — where the saved results are and how to recalculate them.
- [Version register](EXPERIMENT_VERSIONS.md) — how `ours`, the extraction modes and the iterations `ours2`–`ours4` differ.

**Note:** "active" describes the content of **this version of the repository**; it is not a promise that the historical experiment with the new code will give the same model answers. For D23–D44 the *post hoc* status is kept even when the corresponding scripts work now.
