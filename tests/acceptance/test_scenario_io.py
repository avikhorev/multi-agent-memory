"""Spec section 3: scenario file is a JSON object; load/dump round trip."""
from mam.scenario import (
    ActionPattern, Checkpoint, CheckpointAction, CheckpointAnswer,
    CheckpointContext, Constraint, Event, Scenario, Session, dump, load,
)
from mam.types import Fact


def tiny():
    fact = Fact(id="fa-0001", entity="Atlas/billing", attribute="budget_usd", value="250000",
                valid_from=3, valid_to=None, supersedes=None, source="user")
    event = Event(id="e-0001", type="user_message", text="The budget is USD 250,000.",
                  author="user", scope="task", tool=None, args=None, facts=["fa-0001"], factor=False)
    cp = Checkpoint(
        id="cp-1", session=1, role="planner", task_text="Budget?", kind="value",
        context=CheckpointContext(present=["250000"], absent=[], absent_outside_quoted=[], disputed_both=[]),
        answer=CheckpointAnswer(expect="250000", stale=[], disputed=False),
        action=CheckpointAction(forbidden=[], required=[]),
        required_events=["e-0001"], factor=False)
    con = Constraint(id="k-1", text="No.", introduced_in=1, event_id="e-0001",
                     forbidden=[ActionPattern(tool="update_record", args={"field": "x"})])
    return Scenario(id="C0-dev-0000", category="C0", split="dev", seed=0, variant="none",
                    resolution="none", n_sessions=1, sessions=[Session(index=1, events=[event])],
                    facts=[fact], constraints=[con], checkpoints=[cp])


def test_round_trip(tmp_path):
    path = tmp_path / "s.json"
    dump(tiny(), path)
    assert load(path) == tiny()


def test_dump_is_sorted_indented_json_with_trailing_newline(tmp_path):
    path = tmp_path / "s.json"
    dump(tiny(), path)
    text = path.read_text(encoding="utf-8")
    assert text.startswith('{\n  "category": "C0",\n  "checkpoints": [\n')
    assert text.endswith("}\n")
    assert '"valid_to": null' in text


def test_load_changes_detected(tmp_path):
    path = tmp_path / "s.json"
    dump(tiny(), path)
    other = tiny()
    other.facts[0] = Fact(id="fa-0001", entity="Atlas/billing", attribute="budget_usd", value="250001",
                          valid_from=3, valid_to=None, supersedes=None, source="user")
    assert load(path) != other
