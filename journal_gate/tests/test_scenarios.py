import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

import pytest

from journal_gate import scenarios as gen
from mam.extract import _CONSTRAINT
from mam.scenario import dumps, load
from mam.scoring import normalize, score_action
from mam.simulate import Simulator, entries

FILES = sorted(gen.DATA_DIR.glob("*.json"))


def loaded(category):
    return [load(p) for p in FILES if p.name.startswith(category)]


def texts(s):
    return [e.text for sess in s.sessions for e in sess.events]


def event(s, event_id):
    return next(e for sess in s.sessions for e in sess.events if e.id == event_id)


def act(value, field="x.y"):
    return {"tool": "update_record", "args": {"field": field, "value": value}}


def test_files():
    assert len(FILES) == 16
    for c in gen.TYPES:
        assert len(loaded(c)) == 4


def test_deterministic():
    for p in FILES:
        s = load(p)
        assert dumps(gen.generate(s.category, int(s.id[-4:]))) == p.read_text(encoding="utf-8")


def test_load_and_feed():
    for p in FILES:
        s = load(p)
        assert s.split == "journal" and s.n_sessions == 10 and len(entries(s)) > 10
        assert Simulator(s).call("update_record", {"value": "1"}).startswith("OK")


def test_one_checkpoint():
    for p in FILES:
        (cp,) = load(p).checkpoints
        assert cp.role == "worker" and cp.factor and cp.kind in ("constraint", "value")
        assert all(e.id.startswith("x-") for e in map(lambda i: event(load(p), i), cp.required_events) if e.factor)


def test_patterns():
    for s in loaded("J1"):
        cp = s.checkpoints[0]
        assert cp.action.forbidden and not cp.action.required
    for c in ("J2", "J3", "J4"):
        for s in loaded(c):
            cp = s.checkpoints[0]
            assert cp.action.required and not cp.action.forbidden


def test_bans_vs_constraint_regex():
    for c, matches in (("J1", False), ("J2", False), ("J3", True)):
        for s in loaded(c):
            (con,) = s.constraints
            assert bool(_CONSTRAINT.search(con.text)) is matches
            assert con.text in texts(s)
    assert len(gen.BANS) >= 6 and not any(_CONSTRAINT.search(b) for b in gen.BANS)


def test_ban_not_overwritten():
    for c in ("J1", "J2"):
        for s in loaded(c):
            assert s.constraints[0].event_id in {e.id for sess in s.sessions for e in sess.events}


def test_money_normalization():
    s = loaded("J2")[0]
    cp = s.checkpoints[0]
    cp.action.required[0].args["value"] = "300000"
    assert score_action(s, cp.id, act("USD 300,000", "billing.budget_usd")).passed
    assert score_action(s, cp.id, act("300000")).passed
    assert not score_action(s, cp.id, act("300001")).passed
    assert gen.display("money", "300000") == "USD 300,000"


@pytest.mark.parametrize("category", gen.TYPES)
def test_good_and_wrong_action(category):
    for s in loaded(category):
        cp = s.checkpoints[0]
        pat = (cp.action.forbidden or cp.action.required)[0]
        value = pat.args["value"]
        hit = score_action(s, cp.id, act(value)).passed
        miss = score_action(s, cp.id, {"tool": "none", "args": {}}).passed
        other = score_action(s, cp.id, act("no-such-value")).passed
        if category == "J1":
            assert not hit and miss and other
        else:
            assert hit and not miss and not other


def test_j4_value_absent():
    for s in loaded("J4"):
        value = s.checkpoints[0].action.required[0].args["value"]
        alltext = normalize(" ".join(texts(s) + [c.task_text for c in s.checkpoints]))
        assert normalize(value) not in alltext
        assert value in [f.value for f in s.facts]


def test_unique_values():
    for c in ("J1", "J2", "J3"):
        for s in loaded(c):
            cp = s.checkpoints[0]
            value = normalize((cp.action.forbidden or cp.action.required)[0].args["value"])
            base = [t for sess in s.sessions for e in sess.events if not (e.factor and e.type == "user_message" and value in normalize(e.text)) for t in [e.text]]
            assert value not in normalize(" ".join(base))
