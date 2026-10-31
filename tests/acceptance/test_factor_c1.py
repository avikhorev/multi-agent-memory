"""Spec sections 6, 12.2, 12.3: C1 (updates), explicit and implicit variants."""
import calendar
import datetime
import re

import pytest

from mam.generate import control_of, generate, strip_factor
from mam.scenario import dumps
from mam.scoring import normalize
from mam.validate import validate

EXPLICIT = [generate("C1", 100 + i, variant="explicit") for i in range(0, 60, 3)]
IMPLICIT = [generate("C1", 100 + i, variant="implicit") for i in range(60)]
ALL = EXPLICIT + IMPLICIT
LABELS = {"go_live_date": "go-live date", "handover_date": "handover date", "uat_start_date": "uat start date",
          "budget_usd": "budget", "contingency_usd": "contingency reserve", "user_count": "pilot user count",
          "owner": "owner",
          "tech_lead": "tech lead", "integration": "integration partner", "data_source": "data source"}


def factor_events(s):
    return [e for sess in s.sessions for e in sess.events if e.factor]


def update_facts(s):
    return [f for f in s.facts if f.supersedes is not None]


def fact(s, fid):
    return next(f for f in s.facts if f.id == fid)


def test_all_generated_c1_scenarios_validate():
    for s in ALL:
        assert validate(s) == [], s.id


def test_strip_factor_equals_control():
    for s in ALL[:30]:
        assert strip_factor(s) == control_of(s)
        assert dumps(strip_factor(s)) == dumps(control_of(s))


def test_control_is_the_c0_world_of_the_same_seed():
    s = IMPLICIT[4]
    c0 = generate("C0", s.seed)
    ctl = control_of(s)
    assert ctl.sessions == c0.sessions and ctl.facts == c0.facts and ctl.checkpoints == c0.checkpoints
    assert (ctl.id, ctl.category, ctl.variant) == (s.id, "C1", s.variant)


def test_factor_adds_one_update_and_one_stale_checkpoint():
    for s in ALL:
        assert len(factor_events(s)) == 1 and factor_events(s)[0].type == "user_message"
        assert len(update_facts(s)) == 1
        factor_cps = [c for c in s.checkpoints if c.factor]
        assert len(factor_cps) == 1 and len(s.checkpoints) == 4
        cp = factor_cps[0]
        new = update_facts(s)[0]
        old = fact(s, new.supersedes)
        assert cp.kind == "value" and cp.answer.expect == new.value and cp.context.present == [new.value]
        assert cp.answer.stale == [old.value] and cp.context.absent == [old.value]
        assert cp.required_events == [factor_events(s)[0].id]


def test_update_semantics_in_ground_truth():
    for s in ALL:
        new = update_facts(s)[0]
        old = fact(s, new.supersedes)
        assert (new.entity, new.attribute) == (old.entity, old.attribute)
        assert old.valid_to == new.valid_from and new.valid_to is None and new.valid_from > old.valid_from
        assert new.source == "user"
        assert new.value != old.value
        ev = factor_events(s)[0]
        assert ev.facts == [new.id]


def test_update_comes_after_the_original_and_before_the_checkpoint():
    for s in ALL:
        new = update_facts(s)[0]
        old = fact(s, new.supersedes)
        first_old = min(sess.index for sess in s.sessions for e in sess.events if old.id in e.facts and not e.factor)
        upd = next(sess.index for sess in s.sessions for e in sess.events if e.factor)
        cp = next(c for c in s.checkpoints if c.factor)
        assert first_old < upd < cp.session

    for s in ALL:
        asked = {c.answer.expect for c in s.checkpoints if not c.factor}
        assert fact(s, update_facts(s)[0].supersedes).value not in asked


def test_explicit_update_names_attribute_and_both_values():
    for s in EXPLICIT:
        new = update_facts(s)[0]
        old = fact(s, new.supersedes)
        text = normalize(factor_events(s)[0].text)
        assert normalize(new.value) in text and normalize(old.value) in text
        assert LABELS[new.attribute] in text


def test_implicit_update_has_neither_new_value_nor_attribute_name():
    for s in IMPLICIT:
        new = update_facts(s)[0]
        text = normalize(factor_events(s)[0].text)
        assert normalize(new.value) not in text
        assert LABELS[new.attribute] not in text and new.attribute not in text
        assert not re.search(r"\d{4}-\d\d-\d\d", text)


WORDS = {"two": 2, "three": 3, "four": 4}


def expected_from_text(s):
    """Independent oracle: recompute the new value from the sentence and the old value."""
    new = update_facts(s)[0]
    old = fact(s, new.supersedes)
    text = factor_events(s)[0].text
    if m := re.search(r"slip .* by about (\w+) weeks", text):
        return "slip", str(datetime.date.fromisoformat(old.value) + datetime.timedelta(days=7 * WORDS[m[1]]))
    if m := re.search(r"pulled in by (\d+) days", text):
        return "pull", str(datetime.date.fromisoformat(old.value) - datetime.timedelta(days=int(m[1])))
    if "last day of the month after" in text:
        d = datetime.date.fromisoformat(old.value)
        year, month = (d.year + (d.month == 12), d.month % 12 + 1)
        return "month_end", str(datetime.date(year, month, calendar.monthrange(year, month)[1]))
    if m := re.search(r"trimmed .* by (\d+) percent", text):
        return "trim", str(int(old.value) * (100 - int(m[1])) // 100)
    if m := re.search(r"extra USD ([\d,]+) on top", text):
        return "extra", str(int(old.value) + int(m[1].replace(",", "")))
    if "grows by half" in text:
        return "half", str(int(old.value) * 3 // 2)
    if "tech lead of" in text:
        tl = next(f for f in s.facts if f.entity == old.entity and f.attribute == "tech_lead")
        return "lead", tl.value
    return "unknown", None


def test_implicit_new_value_is_computed_correctly_for_every_template():
    seen = set()
    for s in IMPLICIT:
        kind, expected = expected_from_text(s)
        assert kind != "unknown", factor_events(s)[0].text
        assert update_facts(s)[0].value == expected, (kind, factor_events(s)[0].text)
        seen.add(kind)
    assert seen == {"slip", "pull", "month_end", "trim", "extra", "half", "lead"}


def test_scoring_reference_and_stale_contexts():
    from mam.scoring import score_action, score_context
    from mam.types import Context, ContextItem

    def ctx(*texts):
        return Context(items=[ContextItem(id=f"i{k}", kind="fact", text=t) for k, t in enumerate(texts)])

    for s in ALL[:30]:
        cp = next(c for c in s.checkpoints if c.factor)
        new, old = cp.answer.expect, cp.answer.stale[0]
        assert score_context(s, cp.id, ctx(f"current value: {new}")).passed
        stale_only = score_context(s, cp.id, ctx(f"current value: {old}"))
        both = score_context(s, cp.id, ctx(f"current value: {new}", f"earlier: {old}"))
        assert not stale_only.passed and stale_only.stale_present
        assert not both.passed and both.stale_present
        assert score_action(s, cp.id, {"answer": f"It is {new}."}).passed
        assert not score_action(s, cp.id, {"answer": f"It is {old}."}).passed
        assert not score_action(s, cp.id, {"answer": f"{new}, formerly {old}"}).passed


def test_variants_do_not_change_the_base():
    a = generate("C1", 103, variant="explicit")
    b = generate("C1", 103, variant="implicit")
    assert strip_factor(a).sessions == strip_factor(b).sessions
    assert dumps(a) != dumps(b)


def test_removing_the_factor_removes_update_and_stale_checkpoint():
    s = IMPLICIT[7]
    t = strip_factor(s)
    assert not factor_events(t) and not update_facts(t)
    assert not any(c.answer.stale for c in t.checkpoints) and len(t.checkpoints) == 3
    assert all(f.valid_to is None for f in t.facts)
    assert len(t.facts) == len(s.facts) - 1


def test_strip_factor_does_not_modify_input():
    s = IMPLICIT[1]
    before = dumps(s)
    strip_factor(s)
    assert dumps(s) == before


def test_validator_catches_implicit_event_that_states_new_value():
    s = generate("C1", 104, variant="implicit")
    new = update_facts(s)[0]
    factor_events(s)[0].text += f" That means {new.value}."
    assert any(e.startswith("R4") for e in validate(s, check_determinism=False))


def test_validator_catches_implicit_event_that_names_the_attribute():
    s = generate("C1", 104, variant="implicit")
    new = update_facts(s)[0]
    factor_events(s)[0].text += f" The {LABELS[new.attribute]} matters."
    assert any(e.startswith("R4") for e in validate(s, check_determinism=False))


def test_validator_catches_explicit_event_missing_the_value():
    s = generate("C1", 100, variant="explicit")
    new = update_facts(s)[0]
    factor_events(s)[0].text = "Something changed, details to follow."
    assert any(e.startswith("R2") for e in validate(s, check_determinism=False))


def test_stale_collision_is_caught():
    s = generate("C1", 100, variant="explicit")
    cp = next(c for c in s.checkpoints if c.factor)
    cp.answer.stale = [cp.answer.expect[:-1]]
    cp.context.absent = [cp.answer.expect[:-1]]
    assert validate(s, check_determinism=False) != []


@pytest.mark.parametrize("seed", [100, 107, 119])
def test_c1_is_deterministic(seed):
    assert dumps(generate("C1", seed, variant="implicit")) == dumps(generate("C1", seed, variant="implicit"))
