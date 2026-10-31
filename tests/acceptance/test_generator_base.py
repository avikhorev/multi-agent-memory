"""Spec sections 3, 6 (C0) and 12.1: base generator."""
import re

from mam.generate import generate
from mam.scenario import dumps
from mam.scoring import normalize

SEEDS = [0, 1, 2, 7, 19]


def c0(seed, n=10):
    return generate("C0", seed, n_sessions=n)


def test_same_seed_gives_identical_bytes():
    for seed in SEEDS:
        assert dumps(c0(seed)).encode() == dumps(c0(seed)).encode()


def test_different_seeds_give_different_scenarios():
    texts = {dumps(c0(seed)) for seed in SEEDS}
    assert len(texts) == len(SEEDS)
    a, b = c0(0), c0(1)
    assert [e.text for s in a.sessions for e in s.events] != [e.text for s in b.sessions for e in s.events]
    assert [f.value for f in a.facts] != [f.value for f in b.facts]


def test_header_fields():
    s = generate("C0", 5, split="dev", scenario_id="C0-dev-0005")
    assert (s.id, s.category, s.split, s.seed, s.variant, s.resolution, s.n_sessions) == (
        "C0-dev-0005", "C0", "dev", 5, "none", "none", 10)
    assert [x.index for x in s.sessions] == list(range(1, 11))


def test_session_event_counts_follow_spec():
    for seed in SEEDS:
        for sess in c0(seed).sessions:
            kinds = [e.type for e in sess.events]
            assert kinds.count("user_message") == 1
            assert 0 <= kinds.count("tool_data") <= 2
            assert 0 <= kinds.count("note") <= 3
            assert kinds == sorted(kinds, key=["user_message", "tool_data", "note"].index)


def test_event_field_conventions():
    s = c0(3)
    seen = set()
    for sess in s.sessions:
        for e in sess.events:
            assert e.id not in seen and re.fullmatch(r"e-\d{4}", e.id)
            seen.add(e.id)
            assert e.factor is False
            if e.type == "user_message":
                assert (e.author, e.scope, e.tool, e.args) == ("user", "task", None, None)
            elif e.type == "tool_data":
                assert e.author == "tool" and e.tool in ("read_document", "read_status") and e.args
            else:
                assert e.author in ("planner", "worker", "reviewer") and e.scope in ("task", "shared")
                assert e.tool is None and e.args is None


def test_each_fact_is_reported_and_text_contains_value():
    s = c0(4)
    events = {e.id: e for sess in s.sessions for e in sess.events}
    for fact in s.facts:
        reporters = [e for e in events.values() if fact.id in e.facts]
        assert reporters
        assert all(normalize(fact.value) in normalize(e.text) for e in reporters)
        assert fact.valid_to is None and fact.supersedes is None
        assert (fact.entity == "Atlas" or fact.entity.startswith("Atlas/"))


def test_values_are_normalized():
    s = c0(6)
    for f in s.facts:
        if f.attribute.endswith("_date"):
            assert re.fullmatch(r"2026-\d\d-\d\d", f.value)
        if f.attribute.endswith("_usd") or f.attribute == "user_count":
            assert re.fullmatch(r"[1-9]\d+", f.value)


def test_keys_are_unique_in_c0():
    s = c0(8)
    keys = [(f.entity, f.attribute) for f in s.facts]
    assert len(keys) == len(set(keys))


def test_three_value_checkpoints_in_last_three_sessions():
    for seed in SEEDS:
        s = c0(seed)
        assert [cp.session for cp in s.checkpoints] == [8, 9, 10]
        assert [cp.kind for cp in s.checkpoints] == ["value"] * 3
        assert not any(cp.factor for cp in s.checkpoints)
        facts_by_value = {f.value: f for f in s.facts}
        for cp in s.checkpoints:
            assert cp.context.present == [cp.answer.expect]
            fact = facts_by_value[cp.answer.expect]
            first = min(sess.index for sess in s.sessions for e in sess.events if fact.id in e.facts)
            assert first <= 7
            assert cp.answer.stale == [] and cp.context.absent == []
            ids = {e.id for sess in s.sessions for e in sess.events if fact.id in e.facts}
            assert set(cp.required_events) == ids


def test_asked_facts_are_distinct():
    s = c0(9)
    assert len({cp.answer.expect for cp in s.checkpoints}) == 3


def test_event_time_grows_with_session():
    s = c0(2)
    first_session = {}
    for sess in s.sessions:
        for e in sess.events:
            for fid in e.facts:
                first_session.setdefault(fid, sess.index)
    for f in s.facts:
        sess = first_session[f.id]
        assert 7 * (sess - 1) <= f.valid_from <= 7 * (sess - 1) + 6


def test_c6_length_scales_events():
    short, long_ = c0(3, 10), generate("C6", 3, n_sessions=30)
    assert len(long_.sessions) == 30
    assert len(long_.facts) > 2 * len(short.facts)
    assert [cp.session for cp in long_.checkpoints] == [28, 29, 30]
    firsts = {}
    for sess in long_.sessions:
        for e in sess.events:
            for fid in e.facts:
                firsts.setdefault(fid, sess.index)
    by_value = {f.value: f for f in long_.facts}
    asked = [firsts[by_value[cp.answer.expect].id] for cp in long_.checkpoints]
    assert asked[0] == 1 and asked[1] == 2 and 24 <= asked[2] <= 27
