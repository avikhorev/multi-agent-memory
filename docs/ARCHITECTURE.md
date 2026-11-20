# Architecture

This shows the path of the data: scenario → agent calls → records in memory → context → evaluation. The main code is [`live.py`](../src/mam/live.py), [`agents.py`](../src/mam/agents.py) and [`systems/ours.py`](../src/mam/systems/ours.py). The interface rules are in [`SCENARIO_FORMAT.md`](SCENARIO_FORMAT.md), the risks in [`THREAT_MODEL.md`](THREAT_MODEL.md). A **practical example** with the saved events and agent answers is in [`WALKTHROUGH.md`](WALKTHROUGH.md).

**Navigation:** section 1 — the whole system; 2 — one session; 3 — writing and reading `ours`; 4 — version resolution; 5–6 — context growth and failure diagnosis. The nodes of the diagrams contain links to the code at commit `1811222`; the line numbers refer to it, not to the current version.

**Visual version:** [static map of the four stages](img/visual-story.svg) · [interactive tour of the real traces](demo/README.md). The Mermaid diagram below shows the structure of all components; the demo separately shows which events were **actually** recorded in the selected run.

## 1. The whole system

Between calls the agents keep no state. The context is assembled by the replaceable implementation [`MemorySystem`](../src/mam/systems/base.py#L21); in [`memory_eval.py`](../src/mam/memory_eval.py) the same interface is checked without LLM agents.

```mermaid
flowchart TB
    scenario["Scenario<br/>sessions and checks"] --> loop

    subgraph harness["Live run: run_live"]
        loop["Session loop"]
        sim["Simulator<br/>Worker tools"]
        scorer["Evaluator<br/>checks and failure labels"]
    end

    subgraph memory["Memory"]
        api["MemorySystem<br/>write, context, end_session"]
    end

    subgraph agents["Stateless agents"]
        planner["Planner"]
        worker["Worker"]
        reviewer["Reviewer"]
    end

    llm["LLMClient<br/>ClaudeCliClient<br/>claude-haiku-5-5"]
    results["Units in results/live/<br/>tables and REPORT.md"]

    loop <-->|"writes and context up to 2000 tokens"| api
    loop <-->|"context and task, answer and action"| agents
    loop <--> sim
    loop --> scorer
    scorer --> results
    agents --> llm
    api -.->|"fact extraction, ours only"| llm

    click scenario href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/docs/SCENARIO_FORMAT.md"
    click loop href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L130-L203"
    click sim href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/simulate.py#L14"
    click scorer href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/scoring.py#L95"
    click api href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/base.py#L21"
    click planner href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/agents.py#L22"
    click worker href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/agents.py#L25"
    click reviewer href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/agents.py#L31"
    click llm href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/llm.py#L69"
    click results href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/results/live/main/tables.md"
```

## 2. One session

Per session the model is called four times: Planner (1), Worker (2), Reviewer (1). The Worker first chooses an action, then receives the result of the tool. **Both Worker calls use one context**: the document read comes directly as the tool result. The new facts of `ours` appear only after `end_session`.

```mermaid
sequenceDiagram
    autonumber
    participant H as run_live loop
    participant M as Memory
    participant P as Planner
    participant W as Worker
    participant S as Simulator
    participant R as Reviewer
    participant E as Evaluator

    H->>M: write, user messages,<br/>scenario notes and drafts

    H->>M: context for Planner
    M-->>H: context
    H->>P: context, message, task
    P-->>H: task for Worker, notes
    H->>M: write, Planner notes

    H->>M: context for Worker
    M-->>H: context
    H->>W: context, task, this session's source
    W-->>H: one action
    alt read_document or read_status
        H->>S: tool call
        S-->>H: source text
        H->>M: write, source with trust untrusted
    else update_record
        H->>S: tool call
        S-->>H: result
    else none
        Note over H: no tool called
    end
    H->>W: same context and tool result
    W-->>H: answer, notes
    opt update_record chosen in the second call
        H->>S: tool call
    end
    H->>M: write, Worker notes

    H->>M: context for Reviewer
    M-->>H: context
    H->>R: context and result to review
    R-->>H: accept or reject, notes
    H->>M: write, Reviewer notes

    H->>E: this session's checks
    E-->>H: passed or not, failure label

    H->>M: end_session
    Note over M: ours extracts facts of the closed session
```

The step numbers match the numbers in the diagram.

| Steps | What happens | Code |
|---|---|---|
| 1 | write of the scenario's messages and notes | [`live.py:131-135`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L131-L135) |
| 2–3 | context for Planner | [`live.py:141`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L141) |
| 4–5 | Planner call | [`live.py:142`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L142) |
| 6 | Planner notes | [`live.py:143`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L143) |
| 7–8 | context for Worker, one for both calls | [`live.py:148`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L148) |
| 9–10 | first Worker call | [`live.py:151`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L151) |
| 11–12 | reading the source | [`live.py:154-155`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L154-L155) |
| 13 | writing the source as `untrusted` | [`live.py:156-162`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L156-L162) |
| 14–15 | `update_record` in the first call | [`live.py:163-164`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L163-L164) |
| 16–17 | second Worker call | [`live.py:167`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L167) |
| 18 | `update_record` in the second call | [`live.py:169-171`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L169-L171) |
| 19 | Worker notes | [`live.py:172`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L172) |
| 20–21 | context for Reviewer | [`live.py:176`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L176) |
| 22–23 | Reviewer call | [`live.py:177`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L177) |
| 24 | Reviewer notes | [`live.py:178`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L178) |
| 25–26 | checks and failure labels | [`live.py:181-198`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L181-L198) |
| 27 | `end_session` | [`live.py:200-201`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L200-L201) |

**Where to find the steps in the code:** the recording and the calls are in [`run_live`](../src/mam/live.py); the parsing of the answer and the role are in [`run_agent`](../src/mam/agents.py); the tool simulation is in [`simulate.py`](../src/mam/simulate.py); the checks are in [`scoring.py`](../src/mam/scoring.py). The numbers in the diagram show the order of the operations. The dashed line in the animation marks the direct passing of a task between roles, bypassing memory.

![Steps of one session: from user messages to end_session, two direct paths around memory](img/session-steps.svg)

## 3. Memory `ours`

`write` saves the original record. `end_session` extracts the facts and constraints, and `context` selects the versions available to the reader and assembles the text within the limit. **The current value is computed at read time**, after the visibility filter.

The memory `ours` exists only in the RAM of one run unit. It is not restored from files: the runner saves the results and traces to disk, but not its state.

![Write path through memory ours: six steps from write to disk](img/memory-flow.svg)

For reading the order matters: **pinned constraints → facts → fragments**. Records unsuitable for the scope and quarantined records are excluded. If the constraints do not fit within the limit, the system reports an error instead of cutting them.

```mermaid
flowchart TB
    subgraph writing["Writing"]
        entry["write: the record is saved"]
        close["end_session: session records in clock order"]
        extractor["Extractor<br/>facts with date and source"]
        rule["rule_constraints<br/>trusted records only"]
        guard["split_untrusted<br/>split by lines"]
        entry --> close
        close --> extractor
        close --> rule
        close -->|"untrusted documents<br/>and tool outputs"| guard
    end

    subgraph stores["Stores"]
        versions["Fact versions<br/>by entity and attribute key"]
        constraints["Pinned constraints"]
        fragments["quoted_data fragments"]
        quarantine["Quarantine<br/>does not enter the context"]
    end

    extractor --> versions
    rule --> constraints
    guard -->|"value not extracted as a fact"| fragments
    guard -->|"looks like an instruction"| quarantine

    subgraph reading["Reading: context"]
        scope["Visibility filter<br/>private, task, shared"]
        first["Constraints go first<br/>error if they do not fit the limit"]
        resolve["Facts<br/>version resolution, DISPUTED and data labels"]
        rest["Fragments"]
        rank["Selection by BM25 and time<br/>facts first, then fragments"]
        limit["Filling up to 2000 tokens"]
        scope --> first
        scope --> resolve
        scope --> rest
        resolve --> rank
        rest --> rank
        first --> limit
        rank --> limit
    end

    constraints --> scope
    versions --> scope
    fragments --> scope

    click entry href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/base.py#L28"
    click close href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L50-L54"
    click extractor href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/extract.py#L230"
    click rule href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/extract.py#L39"
    click guard href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/guard.py#L29"
    click versions href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L74-L76"
    click constraints href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L62-L64"
    click fragments href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L68-L70"
    click quarantine href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L71"
    click scope href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/base.py#L8"
    click first href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L169-L175"
    click resolve href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L140"
    click rest href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L180-L182"
    click rank href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L183-L185"
    click limit href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L186-L190"
```

[`split_untrusted`](../src/mam/guard.py#L29) passes ordinary lines through as data and moves lines with signs of injection into quarantine; the extracted fact is stored separately from the source text. The example in the animation is illustrative.

![Three lines of a document pass through the filter: a fact, data and quarantine](img/injection-guard.svg)

An example of a real context assembly for one question — `C1-eval-0012` from `data/eval`; for `ours` the saved extractor cache was used.

![Context of ours, full_history and shared_rag_bm25 for one question about the current value](img/same-question.svg)

**Post-freeze iterations** are in `scripts/` and do not change the main `src/mam`:

| Variant | What is added | Code |
|---|---|---|
| `ours2` | a buffer of the records of the open session; the rest of the limit is filled with old records by BM25, except untrusted ones and records with losing values; an untrusted value newer than a trusted one is shown as a dispute | [`scripts/post_hoc_ours2.py`](../scripts/post_hoc_ours2.py) |
| `ours3` | losing values are replaced by `[outdated]`, the record stays; filling up to 300 tokens | [`scripts/post_hoc_ours2.py`](../scripts/post_hoc_ours2.py) |
| `ours4` | the extractor also returns constraints; accepted only from trusted records and merged with the rule's result | [`scripts/post_hoc_ours4.py`](../scripts/post_hoc_ours4.py) |

The order under the limit for `ours2`–`ours4`: constraints, buffer, facts, fragments, filling.

## 4. Conflict resolution

`_resolve` goes through the visible versions in write order. When the values differ, it takes into account trust, the event time, and then the authority of the source (`user` > `tool` > `document` > `agent`). If the time is not stated in the text, the version is considered the last one. **The result may depend on the order of writing** — see section 9 of [`REPORT.md`](../REPORT.md).

```mermaid
flowchart TD
    next["Next visible version of the key"] --> dated{"Event time<br/>stated in the text?"}
    dated -->|"no"| assume["Consider it the last one:<br/>time = maximum + 1"]
    dated -->|"yes"| same
    assume --> same{"Is this value<br/>already in effect?"}
    same -->|"yes"| confirm["The value stays,<br/>the more trusted source is kept"]
    same -->|"no"| empty{"Is there a value<br/>in effect?"}
    empty -->|"no"| accept["Accept"]
    empty -->|"yes"| trust{"Is the version untrusted,<br/>and the current one is not?"}
    trust -->|"yes"| rejectTrust["Reject: an untrusted source<br/>does not change a trusted fact"]
    trust -->|"no"| time{"Compare the event time"}
    time -->|"newer"| later["Replace: later_event"]
    time -->|"older"| rejectOld["Reject: older event"]
    time -->|"equal"| authority{"Compare authority"}
    authority -->|"higher"| replace["Replace: authority"]
    authority -->|"lower"| rejectLow["Reject: lower authority"]
    authority -->|"equal"| disputed["Keep both values:<br/>DISPUTED"]

    click next href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L104"
    click dated href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L106"
    click assume href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L107"
    click same href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L109"
    click confirm href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L110-L112"
    click empty href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L113"
    click accept href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L114"
    click trust href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L115"
    click rejectTrust href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L116-L117"
    click time href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L120"
    click later href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L121-L122"
    click rejectOld href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L123-L124"
    click authority href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L125"
    click replace href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L126-L127"
    click rejectLow href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L128-L129"
    click disputed href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L130-L132"
```

The animation shows four cases of resolving one attribute; the values are illustrative.

![Conflict resolution: newer replaces, untrusted does not replace, older is rejected, equal ones stay as DISPUTED](img/conflict-resolution.svg)

## 5. Context filling

The growth of the Worker's context in the 30-session scenario C6: tokens and the share of the original records that got into the context. For `ours` the share is not comparable: the system outputs facts and fragments instead of records.

![Growth of the Worker's context by session: tokens within the 2000 limit for four systems](img/context-growth.svg)

## 6. Failure label

For a failed checkpoint, [`label_failure`](../src/mam/scoring.py#L118) distinguishes a provider refusal, an unread source, a context error and an answer error. The label `agent` depends, among other things, on the memory system: its context affects the choice of tool.

![Chain of checks by which a failure label is assigned to a checkpoint](img/failure-label.svg)
