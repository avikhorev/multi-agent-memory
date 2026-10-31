"""Spec section 6, C2: pinned constraint and a later task that would violate it."""
import re

from mam.generate import generate, strip_factor, control_of
from mam.scenario import dumps
from mam.scoring import score_action, score_context
from mam.types import Context, ContextItem
from mam.validate import validate

SCENARIOS = [generate("C2", 200 + i) for i in range(30)]


def events(s):
    return {e.id: e for sess in s.sessions for e in sess.events}


def test_valid_and_strip_equals_control():
    for s in SCENARIOS:
        assert validate(s) == [], s.id
        assert strip_factor(s) == control_of(s)
        assert not strip_factor(s).constraints


def test_constraint_shape():
    for s in SCENARIOS:
        assert len(s.constraints) == 1
        c = s.constraints[0]
        assert 2 <= c.introduced_in <= 4
        ev = events(s)[c.event_id]
        assert ev.type == "user_message" and ev.factor and ev.text == c.text
        (pat,) = c.forbidden
        assert pat.tool == "update_record" and set(pat.args) == {"field"}
        assert re.fullmatch(r"[a-z]+\.[a-z_]+_(date|usd)|[a-z]+\.[a-z_]+", pat.args["field"])
        assert pat.args["field"] in c.text
        sess = next(x for x in s.sessions if ev in x.events)
        assert sess.index == c.introduced_in


def test_field_names_an_existing_fact_key():
    for s in SCENARIOS:
        field = s.constraints[0].forbidden[0].args["field"]
        mod, attr = field.split(".")
        entity = "Atlas" if mod == "atlas" else f"Atlas/{mod}"
        assert any(f.entity == entity and f.attribute == attr for f in s.facts)


def test_checkpoint_asks_worker_to_violate_after_several_sessions():
    for s in SCENARIOS:
        c = s.constraints[0]
        cp = next(x for x in s.checkpoints if x.factor)
        assert len(s.checkpoints) == 4 and cp.kind == "constraint" and cp.role == "worker"
        assert cp.session - c.introduced_in >= 3
        field = c.forbidden[0].args["field"]
        assert cp.context.present == [field]
        assert field not in cp.task_text
        assert cp.action.forbidden == c.forbidden and cp.action.required == []
        assert cp.answer.expect is None
        assert cp.required_events == [c.event_id]


def reference_context(s):
    c = s.constraints[0]
    return Context(items=[ContextItem(id="k", kind="constraint", text=c.text, entry_ids=(c.event_id,))])


def test_reference_context_passes_and_context_without_constraint_fails():
    for s in SCENARIOS[:10]:
        cp = next(x for x in s.checkpoints if x.factor)
        assert score_context(s, cp.id, reference_context(s)).passed
        facts_only = Context(items=[ContextItem(id="f", kind="fact", text="; ".join(f.value for f in s.facts))])
        assert not score_context(s, cp.id, facts_only).passed


def test_action_scoring_against_the_constraint():
    for s in SCENARIOS[:10]:
        cp = next(x for x in s.checkpoints if x.factor)
        field = s.constraints[0].forbidden[0].args["field"]
        violating = {"tool": "update_record", "args": {"field": field, "value": "1"}, "answer": "", "notes": []}
        other = {"tool": "update_record", "args": {"field": "zzz.other", "value": "1"}, "answer": "", "notes": []}
        idle = {"tool": "none", "args": {}, "answer": "refused", "notes": []}
        assert not score_action(s, cp.id, violating).passed
        assert score_action(s, cp.id, other).passed and score_action(s, cp.id, idle).passed


def test_validator_catches_constraint_tied_to_wrong_event():
    s = generate("C2", 205)
    base_user = next(e for e in s.sessions[0].events if e.type == "user_message")
    s.constraints[0].event_id = base_user.id
    assert any(e.startswith("R2") for e in validate(s, check_determinism=False))


def test_validator_catches_lost_constraint_text():
    s = generate("C2", 205)
    events(s)[s.constraints[0].event_id].text = "Nothing special."
    assert validate(s, check_determinism=False) != []


def test_deterministic():
    assert dumps(generate("C2", 207)) == dumps(generate("C2", 207))
