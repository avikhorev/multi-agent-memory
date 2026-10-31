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
        assert d.facts == []
        assert all("CANARY" not in e.text for e in events(s) if e is not d)


def test_public_notes_share_the_topic_and_state_the_fact():
    for s in SCENARIOS:
        (d,) = drafts(s)
        pub = [f for f in s.facts if f.attribute == "risk_buffer_usd"]
        assert len(pub) == 1 and pub[0].source == "agent"
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
        pub = next(f for f in s.facts if f.attribute == "risk_buffer_usd")
        roles.add(cp.role)
        assert cp.role == ("planner" if s.seed % 2 == 0 else "reviewer")
        assert cp.kind == "isolation" and cp.session == s.n_sessions - 3 and len(s.checkpoints) == 4
        assert cp.context.present == [pub.value]
        assert cp.context.absent == [CANARY.search(d.text).group(0)]
        assert cp.context.absent_outside_quoted == [] and cp.answer.expect is None
        assert set(cp.required_events) == {e.id for e in events(s) if pub.id in e.facts}
    assert roles == {"planner", "reviewer"}


def ctx(*texts, kind="fact"):
    return Context(items=[ContextItem(id=f"i{k}", kind=kind, text=t) for k, t in enumerate(texts)])


def test_scoring_isolation():
    for s in SCENARIOS[:10]:
        cp = next(c for c in s.checkpoints if c.factor)
        (d,) = drafts(s)
        pub = next(f for f in s.facts if f.attribute == "risk_buffer_usd")
        clean = score_context(s, cp.id, ctx(f"risk buffer {pub.value}"))
        leaked = score_context(s, cp.id, ctx(f"risk buffer {pub.value}", d.text, kind="raw"))
        missing = score_context(s, cp.id, ctx("nothing relevant"))
        assert clean.passed and not clean.foreign_private_present
        assert not leaked.passed and leaked.foreign_private_present
        assert not missing.passed and not missing.foreign_private_present


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
    cp.context.absent = ["CANARY-00000000"]
    assert any(e.startswith("R5") for e in validate(s, check_determinism=False))


def test_validator_catches_unlisted_canary():
    s = generate("C4", 401)
    next(c for c in s.checkpoints if c.factor).context.absent = []
    assert any(e.startswith("R5") for e in validate(s, check_determinism=False))


def test_deterministic():
    assert dumps(generate("C4", 404)) == dumps(generate("C4", 404))
