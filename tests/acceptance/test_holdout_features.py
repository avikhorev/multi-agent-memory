"""Structural checks that the hard options do what they are meant to (spec section 10, holdout ideas)."""
import re

import pytest

from mam.generate import day_of, generate_split
from mam.validate import validate

HOLD = {s.id: s for s in generate_split("holdout")}


def events(s):
    return [e for sess in s.sessions for e in sess.events]


def factor_cps(s):
    return [c for c in s.checkpoints if c.factor]


def chain(s):
    return [f for f in s.facts if f.supersedes is not None]


def test_all_validate():
    for s in HOLD.values():
        assert validate(s) == [], s.id


@pytest.mark.parametrize("sid,attr_suffix", [("H-0001", "_date"), ("H-0009", "_usd")])
def test_three_relative_updates_of_one_fact(sid, attr_suffix):
    s = HOLD[sid]
    ups = chain(s)
    assert len(ups) == 3 and s.variant == "implicit"
    assert len({(f.entity, f.attribute) for f in ups}) == 1 and ups[0].attribute.endswith(attr_suffix)
    (cp,) = factor_cps(s)
    assert len(cp.answer.stale) == 3 and cp.answer.expect == ups[-1].value
    assert [f.valid_from for f in ups] == sorted(f.valid_from for f in ups)
    assert not any(re.search(r"\d{4}-\d\d-\d\d", e.text) for e in events(s) if e.factor)


def test_update_after_conflict_in_last_session_but_one():
    s = HOLD["H-0002"]
    conflict, post = factor_cps(s)
    assert conflict.kind == "conflict" and conflict.answer.disputed
    assert post.kind == "value" and post.session == s.n_sessions
    (upd,) = chain(s)
    sess = next(x.index for x in s.sessions for e in x.events if upd.id in e.facts)
    assert sess == s.n_sessions - 1
    assert sorted(post.answer.stale) == sorted(conflict.context.disputed_both[0])


def test_filler_fact_close_to_the_stale_value():
    s = HOLD["H-0003"]
    (cp,) = factor_cps(s)
    stale = cp.answer.stale[0]
    old = next(f for f in s.facts if f.value == stale)
    near = [f for f in s.facts if f.attribute == old.attribute and f.entity != old.entity
            and f.id.startswith("fx-")]
    assert len(near) == 1 and stale not in near[0].value and near[0].value not in stale
    if old.attribute.endswith("_date"):
        assert abs(day_of(near[0].value) - day_of(stale)) <= 3
    else:
        assert abs(int(near[0].value) - int(stale)) <= 2000


def test_user_confirms_a_rule_that_was_only_in_a_document():
    s = HOLD["H-0004"]
    (cp,) = factor_cps(s)
    assert "compliance desk" in cp.context.present
    owners = [e for e in events(s) if "compliance desk" in e.text]
    assert [e.type for e in owners] == ["tool_data"]
    later = [e for e in events(s) if e.factor and e.type == "user_message" and "second rule" in e.text]
    assert len(later) == 1


def test_constraint_after_seven_quiet_sessions():
    s = HOLD["H-0005"]
    c = s.constraints[0]
    (cp,) = factor_cps(s)
    assert c.introduced_in == 2 and cp.session == s.n_sessions == 10
    assert not any(c.forbidden[0].args["field"] in e.text for sess in s.sessions[2:] for e in sess.events)


def test_several_canaries_in_one_private_draft_and_both_readers_checked():
    s = HOLD["H-0006"]
    drafts = [e for e in events(s) if "CANARY-" in e.text]
    assert len(drafts) == 1 and drafts[0].scope == "private"
    assert len(re.findall(r"CANARY-[0-9a-f]{8}", drafts[0].text)) == 3
    cps = factor_cps(s)
    assert {c.role for c in cps} == {"planner", "reviewer"}
    assert all(len(c.context.absent) == 3 for c in cps)


def test_harmless_imperatives_in_several_documents():
    s = HOLD["H-0007"]
    docs = [e for e in events(s) if e.factor and e.type == "tool_data"]
    assert len(docs) == 3 and sum("INJ-" in e.text for e in docs) == 1
    (cp,) = factor_cps(s)
    assert len(cp.context.present) == 5


def test_lower_authority_value_written_after_higher_authority():
    s = HOLD["H-0008"]
    a, b = [f for f in s.facts if f.attribute == "sign_off_date"]
    assert s.resolution == "authority" and a.valid_from == b.valid_from and a.source != b.source
    (cp,) = factor_cps(s)
    win = next(f for f in (a, b) if f.value == cp.answer.expect)
    sessions = {f.id: next(x.index for x in s.sessions for e in x.events if f.id in e.facts) for f in (a, b)}
    other = b if win is a else a
    assert sessions[win.id] < sessions[other.id]


def test_long_scenario_with_look_alike_values_for_old_questions():
    s = HOLD["H-0010"]
    assert s.n_sessions == 30 and s.category == "C6"
    decoys = [f for f in s.facts if f.id.startswith("fx-")]
    assert len(decoys) == 2
    asked = [c.answer.expect for c in s.checkpoints[:2]]
    for d, a in zip(decoys, asked):
        assert d.value != a and d.attribute == next(f for f in s.facts if f.value == a).attribute
