"""Spec sections 6 and 12.2: factor elements exist only where the category adds them."""
import pytest

from mam.generate import control_of, generate, generate_split, strip_factor
from mam.scenario import dumps

DEV = generate_split("dev")


def factor_events(s):
    return [e for sess in s.sessions for e in sess.events if e.factor]


@pytest.mark.parametrize("category", ["C1", "C2", "C3", "C4", "C5", "C6"])
def test_strip_factor_equals_control_for_every_scenario(category):
    scenarios = [s for s in DEV if s.category == category]
    assert len(scenarios) >= 20
    for s in scenarios:
        assert strip_factor(s) == control_of(s), s.id
        assert dumps(strip_factor(s)) == dumps(control_of(s)), s.id


def test_c0_has_no_factor_elements():
    c0 = [s for s in DEV if s.category == "C0"]
    assert len(c0) == 20
    for s in c0:
        assert not factor_events(s)
        assert not any(c.factor for c in s.checkpoints)
        assert not s.constraints
        assert s == control_of(s)


@pytest.mark.parametrize("category", ["C1", "C2", "C3", "C4", "C5"])
def test_categories_c1_to_c5_have_factor_elements(category):
    for s in [x for x in DEV if x.category == category]:
        assert factor_events(s), s.id
        assert any(c.factor for c in s.checkpoints)
        assert s != control_of(s)
        assert 2 <= len(s.checkpoints) <= 4


def test_c6_factor_is_only_length():
    for s in [x for x in DEV if x.category == "C6"]:
        assert not factor_events(s) and not any(c.factor for c in s.checkpoints)
        assert s.n_sessions in (10, 20, 30)
        assert control_of(s).n_sessions == s.n_sessions
        assert [c.session for c in s.checkpoints] == [s.n_sessions - 2, s.n_sessions - 1, s.n_sessions]


def test_control_of_ignores_variant_and_resolution_but_keeps_labels():
    s = generate("C3", 300, variant="implicit", resolution="authority")
    c = control_of(s)
    assert (c.variant, c.resolution, c.category, c.id) == ("implicit", "authority", "C3", s.id)


def test_base_event_ids_do_not_shift_when_a_factor_is_added():
    for category in ("C1", "C3", "C4"):
        s = generate(category, 123, variant="explicit" if category != "C4" else "none",
                     resolution="disputed" if category == "C3" else "none")
        base_ids = [e.id for sess in strip_factor(s).sessions for e in sess.events]
        kept = [e.id for sess in s.sessions for e in sess.events if not e.factor]
        assert base_ids == kept
        assert all(e.id.startswith("x-") for e in factor_events(s))
