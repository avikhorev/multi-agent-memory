"""Spec section 6, C4: private draft with a canary next to public notes on the same topic."""
import re

from mam.generate import control_of, generate, strip_factor
from mam.scenario import dumps
from mam.scoring import score_context
from mam.types import Context, ContextItem
from mam.validate import validate

SCENARIOS = [generate("C4", 400 + i) for i in range(30)]
CANARY = re.compile(r"CANARY-[0-9a-f]{8}")


def events(s):
    return [e for sess in s.sessions for e in sess.events]


def drafts(s):
    return [e for e in events(s) if CANARY.search(e.text)]


def test_valid_and_strip_equals_control():
    for s in SCENARIOS:
        assert validate(s) == [], s.id
        assert strip_factor(s) == control_of(s)
        assert not drafts(strip_factor(s))


def test_canary_only_in_one_private_worker_draft():
    for s in SCENARIOS:
        (d,) = drafts(s)
        assert d.type == "note" and d.author == "worker" and d.scope == "private" and d.factor
        assert len(CANARY.findall(d.text)) == 1
        assert len(d.facts) == 1
        assert all("CANARY" not in e.text for e in events(s) if e is not d)


def private_fact(s):
    (d,) = drafts(s)
    (fid,) = d.facts
    return next(f for f in s.facts if f.id == fid)


def public_fact(s):
    private = private_fact(s)
    (pub,) = [f for f in s.facts if f.attribute == "risk_buffer_usd" and f.id != private.id]
    return pub


def test_private_draft_states_a_different_value_on_the_public_key():
    for s in SCENARIOS:
        (d,) = drafts(s)
        priv, pub = private_fact(s), public_fact(s)
        assert (priv.entity, priv.attribute) == (pub.entity, pub.attribute)
        assert priv.value != pub.value and int(priv.value) > int(pub.value)
        assert f"{int(priv.value):,}" in d.text and f"{int(pub.value):,}" not in d.text
        reporters = [e for e in events(s) if priv.id in e.facts]
        assert reporters == [d]
        others = [f.value.lower() for f in s.facts if f.id != priv.id]
        assert not any(priv.value.lower() in v or v in priv.value.lower() for v in others)


def test_public_notes_share_the_topic_and_state_the_fact():
    for s in SCENARIOS:
        (d,) = drafts(s)
        pub = [public_fact(s)]
        assert pub[0].source == "agent"
        public_events = [e for e in events(s) if pub[0].id in e.facts]
        assert public_events and all(e.factor and e.scope in ("shared", "task") and e.type == "note"
                                     for e in public_events)
        module = "Atlas project" if pub[0].entity == "Atlas" else f"{pub[0].entity.split('/')[1]} module"
        for e in public_events:
            assert "risk buffer" in e.text and module in e.text and f"{int(pub[0].value):,}" in e.text
        assert "risk buffer" in d.text and module in d.text
        assert pub[0].value not in d.text and f"{int(pub[0].value):,}" not in d.text


def test_checkpoint_shape_and_role_alternation():
    roles = set()
    for s in SCENARIOS:
        cp = next(c for c in s.checkpoints if c.factor)
        (d,) = drafts(s)
        pub, priv = public_fact(s), private_fact(s)
        roles.add(cp.role)
        assert cp.role == ("planner" if s.seed % 2 == 0 else "reviewer")
        assert cp.kind == "isolation" and cp.session == s.n_sessions - 3 and len(s.checkpoints) == 4
        assert cp.context.present == [pub.value]
        assert cp.context.absent == [CANARY.search(d.text).group(0), priv.value]
        assert cp.context.absent_outside_quoted == [] and cp.answer.expect is None
        assert set(cp.required_events) == {e.id for e in events(s) if pub.id in e.facts}
    assert roles == {"planner", "reviewer"}


def ctx(*texts, kind="fact"):
    return Context(items=[ContextItem(id=f"i{k}", kind=kind, text=t) for k, t in enumerate(texts)])


def test_scoring_isolation():
    for s in SCENARIOS[:10]:
        cp = next(c for c in s.checkpoints if c.factor)
        (d,) = drafts(s)
        pub, priv = public_fact(s), private_fact(s)
        clean = score_context(s, cp.id, ctx(f"risk buffer {pub.value}"))
        leaked = score_context(s, cp.id, ctx(f"risk buffer {pub.value}", d.text, kind="raw"))
        value_only = score_context(s, cp.id, ctx(f"risk buffer {pub.value}", f"risk buffer {priv.value}"))
        missing = score_context(s, cp.id, ctx("nothing relevant"))
        assert not value_only.passed and value_only.foreign_private_present
        assert clean.passed and not clean.foreign_private_present
        assert not leaked.passed and leaked.foreign_private_present
        assert not missing.passed and not missing.foreign_private_present


def test_validator_accepts_private_fact_next_to_public_one():
    s = generate("C4", 402)
    assert len([f for f in s.facts if f.attribute == "risk_buffer_usd"]) == 2
    assert validate(s) == []


def test_validator_catches_private_value_in_a_public_note():
    s = generate("C4", 401)
    priv = private_fact(s)
    pub = next(e for e in events(s) if e.factor and e.scope != "private")
    pub.text += f" Also USD {int(priv.value):,}."
    assert any(e.startswith("R5") for e in validate(s, check_determinism=False))


def test_validator_catches_canary_in_public_note():
    s = generate("C4", 401)
    pub = next(e for e in events(s) if e.factor and e.scope != "private")
    pub.text += " " + CANARY.search(drafts(s)[0].text).group(0)
    assert any(e.startswith("R5") for e in validate(s, check_determinism=False))


def test_validator_catches_draft_that_is_not_private():
    s = generate("C4", 401)
    drafts(s)[0].scope = "shared"
    assert any(e.startswith("R5") for e in validate(s, check_determinism=False))


def test_validator_catches_checkpoint_canary_missing_from_events():
    s = generate("C4", 401)
    cp = next(c for c in s.checkpoints if c.factor)
    cp.context.absent = ["CANARY-00000000", cp.context.absent[1]]
    assert any(e.startswith("R5") for e in validate(s, check_determinism=False))


def test_validator_catches_private_value_missing_from_absent():
    s = generate("C4", 401)
    cp = next(c for c in s.checkpoints if c.factor)
    cp.context.absent = cp.context.absent[:1]
    assert any(e.startswith("R5") for e in validate(s, check_determinism=False))


def test_validator_catches_unlisted_canary():
    s = generate("C4", 401)
    cp = next(c for c in s.checkpoints if c.factor)
    cp.context.absent = cp.context.absent[1:]
    assert any(e.startswith("R5") for e in validate(s, check_determinism=False))


def test_deterministic():
    assert dumps(generate("C4", 404)) == dumps(generate("C4", 404))
