"""Spec section 6, C3: two agents write different values of one key; resolution rules."""
import datetime
import re

from mam.generate import control_of, generate, strip_factor
from mam.scenario import dumps
from mam.scoring import score_action, score_context
from mam.types import Context, ContextItem
from mam.validate import validate

RES = ["later_event", "later_event", "authority", "disputed", "later_event"]
DAY0 = datetime.date(2026, 1, 5)
AUTH = {"user": 3, "tool": 2, "document": 1, "agent": 0}


def make(i, variant):
    return generate("C3", 300 + i, variant=variant, resolution=RES[i % 5])


SCENARIOS = [make(i, "explicit" if i % 3 == 0 else "implicit") for i in range(60)]
EXPLICIT = [make(i, "explicit") for i in range(30)]


def pair(s):
    facts = [f for f in s.facts if f.attribute == "sign_off_date"]
    assert len(facts) == 2
    return facts


def event_of(s, fact):
    (e,) = [e for sess in s.sessions for e in sess.events if fact.id in e.facts]
    return e


def session_of(s, event):
    return next(x.index for x in s.sessions if event in x.events)


def spec_winner(a, b):
    """Spec section 6, independent of the generator."""
    if a.valid_from != b.valid_from:
        return max((a, b), key=lambda f: f.valid_from)
    if AUTH[a.source] != AUTH[b.source]:
        return max((a, b), key=lambda f: AUTH[f.source])
    return None


def test_valid_and_strip_equals_control():
    for s in SCENARIOS:
        assert validate(s) == [], s.id
        assert strip_factor(s) == control_of(s)
        assert not [f for f in strip_factor(s).facts if f.attribute == "sign_off_date"]


def test_two_agents_two_sessions_two_values():
    for s in SCENARIOS:
        a, b = pair(s)
        assert a.value != b.value and (a.entity, a.attribute) == (b.entity, b.attribute)
        assert a.valid_to is None and b.valid_to is None
        ea, eb = event_of(s, a), event_of(s, b)
        assert {ea.author, eb.author} == {"planner", "worker"}
        assert ea.type == eb.type == "note" and ea.factor and eb.factor
        assert session_of(s, ea) != session_of(s, eb)


def test_resolution_matches_the_spec_rule_and_checkpoint():
    for s in SCENARIOS:
        a, b = pair(s)
        cp = next(c for c in s.checkpoints if c.factor)
        assert cp.kind == "conflict" and len(s.checkpoints) == 4
        win = spec_winner(a, b)
        if s.resolution == "later_event":
            assert a.valid_from != b.valid_from and win is not None
        elif s.resolution == "authority":
            assert a.valid_from == b.valid_from and AUTH[a.source] != AUTH[b.source]
        else:
            assert a.valid_from == b.valid_from and a.source == b.source and win is None
        if win is None:
            assert cp.answer.disputed and cp.answer.expect is None and cp.answer.stale == []
            assert sorted(cp.context.disputed_both[0]) == sorted([a.value, b.value])
            assert cp.context.present == [] and cp.context.absent == []
        else:
            lose = a if win is b else b
            assert not cp.answer.disputed and cp.answer.expect == win.value
            assert cp.context.present == [win.value] and cp.context.absent == [lose.value]
            assert cp.answer.stale == [lose.value] and cp.context.disputed_both == []


def test_both_orders_and_all_resolutions_occur():
    later_first = set()
    for s in SCENARIOS:
        if s.resolution != "later_event":
            continue
        a, b = pair(s)
        win = spec_winner(a, b)
        later_first.add(session_of(s, event_of(s, win)) < session_of(s, event_of(s, b if win is a else a)))
    assert later_first == {True, False}
    assert {s.resolution for s in SCENARIOS} == {"later_event", "authority", "disputed"}


def test_authority_pairs_use_distinct_ranked_sources():
    for s in SCENARIOS:
        if s.resolution == "authority":
            a, b = pair(s)
            assert {a.source, b.source} <= {"user", "tool", "document"} and a.source != b.source


def test_note_text_carries_event_time_and_source():
    phrase = {"user": "user's message", "tool": "status feed", "document": "vendor document"}
    for s in SCENARIOS[:30]:
        for f in pair(s):
            text = event_of(s, f).text
            assert f"as of {DAY0 + datetime.timedelta(days=f.valid_from)}" in text
            assert phrase[f.source] in text


def test_explicit_variant_states_both_values_and_label():
    for s in EXPLICIT:
        for f in pair(s):
            text = event_of(s, f).text.lower()
            assert f.value in text and "sign-off date" in text


def test_implicit_variant_worker_value_is_relative_to_uat_start():
    n = 0
    for s in SCENARIOS:
        if s.variant != "implicit":
            continue
        n += 1
        for f in pair(s):
            e = event_of(s, f)
            if e.author == "planner":
                assert f.value in e.text
            else:
                assert f.value not in e.text and "sign-off date" not in e.text.lower()
                m = re.search(r"(two|three|four|five|six) weeks after UAT starts", e.text)
                weeks = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6}[m[1]]
                uat = next(x for x in s.facts if x.entity == f.entity and x.attribute == "uat_start_date")
                expected = datetime.date.fromisoformat(uat.value) + datetime.timedelta(days=7 * weeks)
                assert f.value == expected.isoformat()
    assert n > 20


def ctx(*items):
    return Context(items=[ContextItem(id=f"i{k}", kind=kind, text=text, disputed=d)
                          for k, (kind, text, d) in enumerate(items)])


def test_scoring_on_conflict_contexts():
    for s in SCENARIOS[:40]:
        a, b = pair(s)
        cp = next(c for c in s.checkpoints if c.factor)
        win = spec_winner(a, b)
        both = ctx(("fact", f"sign-off {a.value} vs {b.value}", True))
        undisputed = ctx(("fact", f"sign-off {a.value} vs {b.value}", False))
        split = ctx(("fact", f"sign-off {a.value}", True), ("fact", f"sign-off {b.value}", True))
        if win is None:
            assert score_context(s, cp.id, both).passed
            assert not score_context(s, cp.id, undisputed).passed
            assert not score_context(s, cp.id, split).passed
            assert score_action(s, cp.id, {"answer": "DISPUTED between two values"}).passed
            assert not score_action(s, cp.id, {"answer": a.value}).passed
        else:
            lose = a if win is b else b
            assert score_context(s, cp.id, ctx(("fact", f"sign-off {win.value}", False))).passed
            assert not score_context(s, cp.id, ctx(("fact", f"sign-off {lose.value}", False))).passed
            assert not score_context(s, cp.id, both).passed
            assert score_action(s, cp.id, {"answer": win.value}).passed
            assert not score_action(s, cp.id, {"answer": f"{win.value} or {lose.value}"}).passed


def test_validator_catches_wrong_resolution():
    s = next(x for x in SCENARIOS if x.resolution == "later_event")
    cp = next(c for c in s.checkpoints if c.factor)
    cp.answer.expect, cp.answer.stale = cp.answer.stale[0], [cp.answer.expect]
    cp.context.present, cp.context.absent = list(cp.answer.stale), list(cp.answer.stale)
    cp.context.present = [cp.answer.expect]
    assert any(e.startswith("R3") for e in validate(s, check_determinism=False))


def test_validator_catches_disputed_marked_resolved():
    s = next(x for x in SCENARIOS if x.resolution == "disputed")
    cp = next(c for c in s.checkpoints if c.factor)
    a, b = cp.context.disputed_both[0]
    cp.answer.disputed, cp.answer.expect = False, a
    cp.context.disputed_both, cp.context.present = [], [a]
    assert any(e.startswith("R3") for e in validate(s, check_determinism=False))


def test_validator_catches_resolved_marked_disputed():
    s = next(x for x in SCENARIOS if x.resolution == "authority")
    cp = next(c for c in s.checkpoints if c.factor)
    a, b = cp.context.present[0], cp.context.absent[0]
    cp.answer.disputed, cp.answer.expect, cp.answer.stale = True, None, []
    cp.context.disputed_both, cp.context.present, cp.context.absent = [[a, b]], [], []
    assert any(e.startswith("R3") for e in validate(s, check_determinism=False))


def test_validator_catches_unexplained_overlap_outside_c3():
    s = generate("C3", 300, variant="explicit", resolution="later_event")
    s.category = "C1"
    assert any(e.startswith("R1") for e in validate(s, check_determinism=False))


def test_deterministic():
    assert dumps(make(2, "implicit")) == dumps(make(2, "implicit"))
