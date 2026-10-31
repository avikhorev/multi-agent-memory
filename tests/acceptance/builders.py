"""Hand-made scenarios and contexts for scorer tests (independent of the generator)."""
from mam.scenario import (
    ActionPattern, Checkpoint, CheckpointAction, CheckpointAnswer, CheckpointContext, Scenario,
)
from mam.types import Context, ContextItem


def make_checkpoint(cp_id="cp-1", role="planner", kind="value", present=(), absent=(), outside=(),
                    both=(), expect=None, stale=(), disputed=False, forbidden=(), required=(),
                    required_events=()):
    return Checkpoint(
        id=cp_id, session=9, role=role, task_text="task", kind=kind,
        context=CheckpointContext(present=list(present), absent=list(absent),
                                  absent_outside_quoted=list(outside),
                                  disputed_both=[list(p) for p in both]),
        answer=CheckpointAnswer(expect=expect, stale=list(stale), disputed=disputed),
        action=CheckpointAction(forbidden=list(forbidden), required=list(required)),
        required_events=list(required_events), factor=False)


def make_scenario(*checkpoints):
    return Scenario(id="X-dev-0000", category="C1", split="dev", seed=1, variant="none",
                    resolution="none", n_sessions=10, sessions=[], facts=[], constraints=[],
                    checkpoints=list(checkpoints))


def make_context(*items):
    """items: (kind, text) or (kind, text, disputed)."""
    out = []
    for i, it in enumerate(items):
        kind, text = it[0], it[1]
        out.append(ContextItem(id=f"i{i}", kind=kind, text=text, entry_ids=(), disputed=bool(len(it) > 2 and it[2]),
                               superseded=False))
    return Context(items=out, token_count=0)


def pattern(tool, **args):
    return ActionPattern(tool=tool, args=args)
