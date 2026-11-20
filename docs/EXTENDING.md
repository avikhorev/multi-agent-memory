# How to add your own memory system

The project has no dynamic plugin registry. To plug your memory into the existing runner, you need to **implement [`MemorySystem`](../src/mam/systems/base.py#L21) and explicitly register the name** in the factory [`mam.systems.create`](../src/mam/systems/__init__.py). After that it can be checked without the model on `dev`, without changing the saved results.

Below is a minimal demonstration `recent_visible`: it keeps only the two latest visible records. This is an **example of the interface**, not a proposed improved baseline system.

## 1. Implementation

Create `src/mam/systems/recent_visible.py`:

```python
from mam.systems.base import MemorySystem, make_context
from mam.tokens import count
from mam.types import Context, ContextItem, Reader


class RecentVisible(MemorySystem):
    def context(self, reader: Reader) -> Context:
        selected: list[ContextItem] = []
        used = 0
        # _visible() first filters by scope/task_id, then sorts by clock.
        for entry in reversed(self._visible(reader)):
            if len(selected) == 2:
                break
            cost = count(entry.text)
            if used + cost > self.limit:
                continue
            selected.append(ContextItem(
                id=f"recent-{entry.id}", kind="raw", text=entry.text,
                entry_ids=(entry.id,),
            ))
            used += cost
        return make_context(list(reversed(selected)))
```

`write` with protection against repeated `id` and `end_session` by default are already implemented in the base class. `Context.token_count` is computed by [`make_context`](../src/mam/systems/base.py). There is **no LLM extraction** here, no conflict resolution and no protection against instructions from a source: this is simple raw memory for checking the connection.

## 2. Register the name

In [`src/mam/systems/__init__.py`](../src/mam/systems/__init__.py):

1. Import `RecentVisible`.
2. Add `"recent_visible"` to the tuple `NAMES`.
3. In `create(...)`, **after the check of the name and the arguments**, add the branch `if name == "recent_visible": return RecentVisible(limit)` before the branches of the existing systems.

Do not change `DEFAULT_SYSTEMS` in [`memory_eval.py`](../src/mam/memory_eval.py): the new system must run explicitly. Do not change the historical tables or the original names `ours`.

For memory with its own LLM calls you additionally need to pass `llm` from [`live.run_live`](../src/mam/live.py) and implement `drain_llm_calls`; for an offline run you need to choose in advance a method of deterministic extraction. The example above does not require this.

## 3. Check the contract before the experiment

Add `tests/unit/test_recent_visible.py`:

```python
from mam.systems import create
from mam.types import Entry, Reader


def entry(id, clock, author, scope, text):
    return Entry(
        id=id, clock=clock, session=1, author=author,
        kind="agent_note", text=text, scope=scope,
        source="agent", trust="agent", origin=None, task_id="task-1",
    )


def test_recent_visible_scope_idempotency_and_limit():
    memory = create("recent_visible", limit=100)
    memory.write(entry("shared", 1, "planner", "shared", "public fact"))
    memory.write(entry("private", 2, "worker", "private", "SECRET"))
    memory.write(entry("latest", 3, "reviewer", "task", "new fact"))
    memory.write(entry("latest", 4, "reviewer", "task", "should be ignored"))
    reader = Reader(role="planner", task_id="task-1", session=1, query="fact")
    context = memory.context(reader)
    assert "public fact" in context.render()
    assert "new fact" in context.render()
    assert "SECRET" not in context.render()
    assert "should be ignored" not in context.render()
    assert context.token_count <= 100
```

Run from the project root after `make venv`:

```bash
make test
```

Additionally check that a context with a small `limit` does not exceed the limit, that another agent's `task` is not visible, and that `write` does not depend on a repeated `id`. A complex system needs checks of `scopes`, `trust`, updates, conflicts and `end_session` — a reference point: the [specification](SCENARIO_FORMAT.md#8-memory-system-interface) and the [existing tests](../tests/acceptance/).

## 4. Compare without the model and without overwriting the archive

The new directory must be **outside** `results/memory_level/eval/`:

```bash
PYTHONPATH=src .venv/bin/python -m mam.memory_eval \
  --split dev --systems recent_visible \
  --out /tmp/mam-recent-visible

PYTHONPATH=src .venv/bin/python -m mam.tables \
  /tmp/mam-recent-visible --title "recent_visible, dev" \
  > /tmp/mam-recent-visible/tables.md
```

The result is `recent_visible.jsonl`, `timing/recent_visible.jsonl` and `tables.md`. The numbers on `dev` **must not** be compared with the main totals on `eval` as one experiment. For an honest paired offline comparison, explicitly run the same systems on **one split and the same scenarios**, in a separate directory, then use `mam.tables`.

## 5. Live experiment: separate and paid

If you need to check the actions of the agents, the runner accepts an explicit `--systems`, but `make live` uses a fixed list and will not pick up the new name automatically. An example after [`make doctor`](RUNBOOK.md#3-live-layer-paid-run):

```bash
PYTHONPATH=src .venv/bin/python -m mam.run live \
  --split dev --select smoke --systems recent_visible \
  --repeats 1 --workers 1 --max-cost-usd 0.25 \
  --out results/live/recent_visible_smoke
```

This is a **paid call**; `--max-cost-usd` is a soft limit that may be exceeded. The result is saved separately; do not use `results/live/main`. This run must not replace the values of the original tables without a new protocol, manifest and [record of the experiment version](EXPERIMENT_VERSIONS.md).

**Before publishing a result:** state the commit, the system name, the source of facts, the token limit, the model version, the split/scenarios, the number of repeats, the definition of the metric and the path to the source files. The conditions matrix is in the [problem statement](PROBLEM.md#comparability-of-systems), the safe verification methods are in the [run guide](RUNBOOK.md).
