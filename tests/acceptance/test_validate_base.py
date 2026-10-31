"""Spec section 5 and 12.1: validator accepts generated scenarios and catches mutations."""
import copy
import dataclasses

from mam.generate import generate
from mam.scenario import dumps
from mam.types import Fact
from mam.validate import validate


def check(s):
    return validate(s, check_determinism=False)


def rules(errors):
    return {e.split(":")[0] for e in errors}


def good():
    return generate("C0", 11)


def asked_fact(s, i=0):
    value = s.checkpoints[i].answer.expect
    return next(f for f in s.facts if f.value == value)


def replace_fact(s, old, **changes):
    s.facts[s.facts.index(old)] = dataclasses.replace(old, **changes)


def test_generated_scenarios_are_valid():
    for seed in range(12):
        assert validate(generate("C0", seed)) == []
    assert validate(generate("C6", 4, n_sessions=30)) == []


def test_value_swap_is_caught():
    s = good()
    f = asked_fact(s)
    replace_fact(s, f, value="2026-12-31")
    assert {"R2", "R3"} <= rules(check(s))


def test_overlapping_intervals_are_caught():
    s = good()
    f = s.facts[0]
    clone = dataclasses.replace(f, id="fa-9999", value="2026-12-30")
    s.facts.append(clone)
    s.sessions[0].events[0].facts.append("fa-9999")
    assert "R1" in rules(check(s))


def test_dangling_valid_to_is_caught():
    s = good()
    replace_fact(s, s.facts[0], valid_to=40)
    assert "R1" in rules(check(s))


def test_lost_event_is_caught():
    s = good()
    f = asked_fact(s)
    for sess in s.sessions:
        sess.events = [e for e in sess.events if f.id not in e.facts]
    errs = check(s)
    assert "R2" in rules(errs)


def test_event_pointing_to_unknown_fact_is_caught():
    s = good()
    s.sessions[2].events[0].facts.append("fa-4040")
    assert "R2" in rules(check(s))


def test_checkpoint_present_missing_from_events_is_caught():
    s = good()
    s.checkpoints[0].context.present = ["2031-01-01"]
    assert "R4" in rules(check(s))


def test_expected_value_must_match_current_fact():
    s = good()
    s.checkpoints[1].answer.expect = "2031-01-01"
    s.checkpoints[1].context.present = ["2031-01-01"]
    assert "R3" in rules(check(s))


def test_absent_that_is_substring_of_current_value_is_caught():
    s = good()
    cp = s.checkpoints[0]
    cp.context.absent = [cp.answer.expect[:-1]]
    assert "R4" in rules(check(s))


def test_canary_in_ordinary_event_is_caught():
    s = good()
    s.sessions[0].events[0].text += " CANARY-0a1b2c3d"
    assert "R5" in rules(check(s))


def test_duplicate_ids_are_caught():
    s = good()
    s.sessions[1].events[0].id = s.sessions[0].events[0].id
    assert "R6" in rules(check(s))


def test_session_numbers_out_of_range_are_caught():
    s = good()
    s.checkpoints[0].session = 11
    assert "R6" in rules(check(s))
    t = good()
    t.n_sessions = 9
    assert "R6" in rules(check(t))


def test_event_counts_per_session_are_checked():
    s = good()
    s.sessions[0].events = [e for e in s.sessions[0].events if e.type != "user_message"]
    assert "R6" in rules(check(s))


def test_non_deterministic_scenario_is_caught_by_regeneration():
    s = good()
    s.sessions[3].events[0].text += " Harmless tampering."
    assert check(s) == []
    assert "R7" in rules(validate(s))


def test_valid_scenario_not_mutated_in_place():
    s = good()
    before = dumps(s)
    validate(s)
    assert dumps(s) == before
