"""Spec section 8 and 12.8: properties 1-8 of the memory systems, tested through the public interface.

mam.systems and mam.tokens are written later by someone else; these tests must fail until they exist.
"""
import pytest

from mam.generate import generate
from mam.scoring import score_context
from mam.simulate import entries
from mam.types import Reader

pytestmark = pytest.mark.memory

ALL = ["ours", "full_history", "sliding_window", "rolling_summary", "shared_rag_bm25"]
LIMITED = ["ours", "sliding_window", "rolling_summary", "shared_rag_bm25"]


def make(name, **kwargs):
    from mam.systems import create
    if name in ("ours", "rolling_summary"):
        kwargs.setdefault("extractor", "rules" if name == "rolling_summary" else "oracle")
    return create(name, **kwargs)


def feed(system, scenario, upto_session, include_end_session=True, repeat=1):
    for e in entries(scenario):
        if e.session > upto_session:
            break
        for _ in range(repeat):
            system.write(e)
    for sess in range(1, upto_session + 1):
        if include_end_session:
            system.end_session(sess)


def reader_for(scenario, cp, role=None):
    return Reader(role=role or cp.role, task_id=f"task-{scenario.id}", session=cp.session, query=cp.task_text)


def factor_cp(scenario):
    return next(c for c in scenario.checkpoints if c.factor)


def context_for(name, scenario, cp=None, **kwargs):
    cp = cp or factor_cp(scenario)
    system = make(name, **kwargs)
    feed(system, scenario, cp.session - 1)
    return system.context(reader_for(scenario, cp)), cp


# property 1: limit
@pytest.mark.parametrize("name", LIMITED)
@pytest.mark.parametrize("limit", [400, 2000])
def test_limit_is_a_ceiling_for_token_count(name, limit):
    from mam.tokens import count
    s = generate("C6", 601, n_sessions=30)
    cp = s.checkpoints[-1]
    ctx, _ = context_for(name, s, cp, limit=limit)
    assert ctx.token_count <= limit
    assert ctx.token_count == sum(count(i.text) for i in ctx.items)


def test_full_history_never_truncates():
    s = generate("C6", 601, n_sessions=30)
    cp = s.checkpoints[-1]
    ctx, _ = context_for("full_history", s, cp, limit=300)
    text = ctx.render()
    for sess in s.sessions[: cp.session - 1]:
        for e in sess.events:
            if e.scope != "private":
                assert e.text in text
    assert ctx.token_count > 300


# property 2: idempotent writes
@pytest.mark.parametrize("name", ALL)
def test_writing_the_same_entry_twice_changes_nothing(name):
    s = generate("C1", 101, variant="explicit")
    cp = factor_cp(s)
    once, twice = make(name), make(name)
    feed(once, s, cp.session - 1)
    feed(twice, s, cp.session - 1, repeat=2)
    r = reader_for(s, cp)
    assert once.context(r) == twice.context(r)


# property 3: private scope
@pytest.mark.parametrize("name", ALL)
@pytest.mark.parametrize("role", ["planner", "reviewer"])
def test_private_draft_of_worker_is_invisible_to_other_roles(name, role):
    s = generate("C4", 402)
    cp = factor_cp(s)
    draft = next(e for sess in s.sessions for e in sess.events if e.scope == "private")
    system = make(name)
    feed(system, s, cp.session - 1)
    for query in (cp.task_text, draft.text):  # the second query matches the draft as strongly as possible
        ctx = system.context(Reader(role=role, task_id=f"task-{s.id}", session=cp.session, query=query))
        assert cp.context.absent[0] not in ctx.render()
        assert draft.text not in ctx.render()


def test_ours_keeps_public_facts_next_to_hidden_draft():
    for seed in (402, 403, 404, 405):
        s = generate("C4", seed)
        ctx, cp = context_for("ours", s)
        assert score_context(s, cp.id, ctx).passed, seed


# property 4: pinned constraints
def test_ours_pins_constraint_for_the_worker_whatever_the_limit():
    from mam.tokens import count
    s = generate("C2", 202)
    cp = factor_cp(s)
    field = cp.context.present[0]
    for limit in (2000, count(s.constraints[0].text) + 40):
        ctx, _ = context_for("ours", s, cp, limit=limit)
        pinned = [i for i in ctx.items if i.kind == "constraint"]
        assert pinned and field in " ".join(i.text for i in pinned)
        assert ctx.token_count <= limit
        assert score_context(s, cp.id, ctx).passed


def test_ours_raises_when_constraints_do_not_fit():
    s = generate("C2", 202)
    cp = factor_cp(s)
    system = make("ours", limit=5)
    feed(system, s, cp.session - 1)
    with pytest.raises(Exception):
        system.context(reader_for(s, cp))


# property 5: validity
@pytest.mark.parametrize("variant,seed", [("explicit", 100), ("implicit", 101), ("implicit", 104)])
def test_ours_closes_old_fact_and_keeps_it_out_of_context(variant, seed):
    s = generate("C1", seed, variant=variant)
    ctx, cp = context_for("ours", s)
    res = score_context(s, cp.id, ctx)
    assert res.passed and not res.stale_present
    assert all(not (i.superseded and cp.answer.stale[0] in i.text) for i in ctx.items)


# property 6: conflicts
@pytest.mark.parametrize("seed,resolution", [(300, "later_event"), (301, "later_event"), (302, "authority"),
                                             (303, "disputed")])
@pytest.mark.parametrize("variant", ["explicit", "implicit"])
def test_ours_resolves_conflicts_by_the_rule(seed, resolution, variant):
    s = generate("C3", seed, variant=variant, resolution=resolution)
    ctx, cp = context_for("ours", s)
    assert score_context(s, cp.id, ctx).passed
    if resolution == "disputed":
        assert any(i.disputed for i in ctx.items)


# property 7: quarantine
def test_ours_quotes_untrusted_content_and_quarantines_instructions():
    for seed in (502, 503, 504):
        s = generate("C5", seed)
        cp = factor_cp(s)
        ctx, _ = context_for("ours", s, cp)
        res = score_context(s, cp.id, ctx)
        assert res.passed and not res.attack_in_instruction_slot
        token = cp.context.absent_outside_quoted[0]
        assert token not in ctx.render()
        untrusted = {e.id for e in entries(s) if e.trust == "untrusted"}
        for item in ctx.items:
            if set(item.entry_ids) & untrusted:
                assert item.kind == "quoted_data"


# property 8: determinism
@pytest.mark.parametrize("name", ALL)
def test_same_entries_same_context(name):
    s = generate("C3", 300, variant="implicit", resolution="later_event")
    cp = factor_cp(s)
    a, b = make(name), make(name)
    feed(a, s, cp.session - 1)
    feed(b, s, cp.session - 1)
    r = reader_for(s, cp)
    assert a.context(r) == b.context(r)
    assert a.context(r).render() == b.context(r).render()


def test_oracle_extractor_is_not_available_for_rolling_summary():
    from mam.systems import create
    with pytest.raises(Exception):
        create("rolling_summary", extractor="oracle")
