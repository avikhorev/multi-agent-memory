# Memory threat model

The system must separate **data** from external sources from **instructions** to agents, and must not pass private records of one role to another. These properties are checked in C4 (isolation) and C5 (instruction injection). The model describes the goal of the protection; the actual limitations of the implementation are given below.

## Trust boundary

| Content | Trust | Rule |
|---|---|---|
| User message via the Planner | `trusted` | Can set the rules of the task |
| The agent's own notes (`notes`) | `agent` | Do not raise the trust of a restated source |
| A document or a tool output | `untrusted` | Data, not a command |

A note based on an untrusted document must inherit its `source` and `trust`. The trust is determined by the weakest source. The goal is to prevent the agent from "laundering" an untrusted instruction through its own restatement.

## What we protect

- The current facts about the project and the user's constraints.
- Private drafts (`private`), available only to their author.
- The instruction slot in the context: the text of an external document must not gain the status of a directive to the agent.

Outside the model: breaking into the storage or the code, collusion of trusted agents, attacks on the LLM provider.

## Threats and measures

| Risk | Example | Protection in `ours` |
|---|---|---|
| **T1: instruction injection** (C5) | A document asks to ignore the rules in the next sessions | Untrusted text is marked as `quoted_data`; lines with signs of injection are sent to quarantine |
| **T2: substitution of a fact** (C1, C5) | An external document changes an approved deadline | When resolving versions, the trust, the event time and the authority of the source are taken into account |
| **T3: leak of private** (C4) | The Reviewer reads the Worker's draft | The visibility-scope filter is applied before search and ranking |
| **T4: laundering of trust** (C5) | An agent restates a command from a document as its own | The note keeps the origin and the trust level of the source data |

Visibility scopes: `private` — only the author; `task` — the participants of the task; `shared` — all agents. The Reviewer receives the result for checking and the available `task`/`shared` records, but not the Worker's private drafts.

## Cost and limits of the protection

The quarantine triggers on signs in the text, not on understanding of the intent. Therefore **false blocks** of admissible phrases are possible (metric `false_block`), and **misses** of attacks without characteristic signs. For example, a line "from now on…" may be a useful fact about the schedule, while a direct order without such words may pass the filter.

The rule for an untrusted source is aimed at protecting a more trusted fact. However, the current algorithm resolves versions in write order: in some orders the protection works incorrectly. The check and an example are given in [`REPORT.md`](../REPORT.md), section 9, and `results/post_hoc/write_order.md`. The filter must not be considered a complete protection against prompt injection.

A legitimate rule from a document requires confirmation by a trusted message from the user. This is not an automatic "unblocking" of an old record: a confirmed rule is processed as new trusted information.
