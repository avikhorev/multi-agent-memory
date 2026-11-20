# Visual tour: one fact, four stages

[**Open the interactive demo**](index.html) · [Static diagram for GitHub](../img/visual-story.svg)

This is a **player of saved traces**, not a simulator or a re-run of the LLM. All answers, Worker actions, labels and numbers are taken from the main run `results/live/main/`, repeat **r0**. You can switch the system `ours` / `full_history` and go through four stages: **source → memory → agent → evaluation**.

| Storyline | Scenario and checkpoint | What you see |
|---|---|---|
| Replacement of a value | `C1-eval-0000`, `cpx-1` | A document with the reserve 727000, the update to 153000, version resolution and different Planner answers |
| Missed document | `C6-eval-0002`, `cp-1` | In `ours` the Worker does not read `D-011`; `full_history` reads it |
| Missed status | `C6-eval-0002`, `cp-3` | In `ours` the Worker does not call `read_status` for `e-0086`; `full_history` calls it |

## How to open

Download or clone the repository and open [`docs/demo/index.html`](index.html) in a browser. No installation is needed, **the file also works via `file://`**: the data is loaded by the local `data.js`, without `fetch()`, a server or API keys. If the browser blocks local files, run this from the repository root:

```bash
python3 -m http.server 8000
```

Then open `http://localhost:8000/docs/demo/`. The interface has a choice of case and system, a jump to any stage, step-by-step playback and links to the source files. The animation starts only on a button press; automatic transitions stop at the fourth stage. With the system reduced-motion mode enabled, the CSS transitions are turned off. There is keyboard navigation between the stages with the arrows.

> GitHub displays `.html` as a source file, not as a finished site. **On the repository page use the [SVG](../img/visual-story.svg)**; open the interactive version locally. This is not GitHub Pages and not external analytics.

## Where the data comes from

The files on which the demo is built:

- [`data/eval/C1-eval-0000.json`](../../data/eval/C1-eval-0000.json), [`data/eval/C6-eval-0002.json`](../../data/eval/C6-eval-0002.json) — events and references.
- [`results/live/main/units/`](../../results/live/main/units) — answers, labels, `context_passed`, `token_count`.
- [`results/live/main/traces/`](../../results/live/main/traces) — `write`, `read`, `extraction`, `resolve`, `agent_action`.

**Not shown:** the exact text of the context. It is not saved in the live trace; `read.item_ids` are references to items, not their content. For example, `frag-e-0017-4` does not prove that the old value from the document was present in the context. The player makes no assumptions about unrecorded facts and does not prove the causality of the labels `agent` or `memory`.

The number of tokens is taken from the `read` of the corresponding role and session and is checked against `checkpoints[].token_count`; the answer from `agent_action` — against the saved `checkpoints[].answer`. The snapshot contains **only the selected** checkpoints of `r0`, so it says nothing about the statistical spread or the average quality of the systems.

## How to update the demo

```bash
python3 scripts/build_visual_demo.py          # update docs/demo/data.js from the frozen JSON/JSONL
python3 scripts/build_visual_demo.py --check  # check that the snapshot is not outdated
make docs-check                              # links, tests, artifacts and the demo snapshot
```

The generator uses only the Python 3.11+ standard library, **does not change** the files in `data/` and `results/`, and does not call the model. After changing the source data, first determine whether the results remain comparable with the frozen experiment; do not present a new run as a historical one. The storylines are changed in `CASES` of the file [`scripts/build_visual_demo.py`](../../scripts/build_visual_demo.py); the interface is in [`demo.js`](demo.js) and [`style.css`](style.css).

Additional analyses: [C1 update](../WALKTHROUGH.md), [C6 source omission](../FAILURE_WALKTHROUGH.md), [evaluator limitations](../KNOWN_ISSUES.md).
