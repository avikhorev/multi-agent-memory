"""Spec sections 4 and 12.4: tool simulator and the feed of memory entries."""
from mam.generate import generate
from mam.simulate import Simulator, entries

S = generate("C0", 21)
TOOL_EVENTS = [e for sess in S.sessions for e in sess.events if e.type == "tool_data"]


def test_scenario_has_tool_events():
    assert len(TOOL_EVENTS) >= 3


def test_call_returns_the_scenario_tool_data_by_tool_and_args():
    sim = Simulator(S)
    for e in TOOL_EVENTS:
        assert sim.call(e.tool, e.args) == e.text


def test_argument_order_does_not_matter():
    sim = Simulator(S)
    e = next(x for x in TOOL_EVENTS if x.tool == "read_status")
    reversed_args = dict(reversed(list(e.args.items())))
    assert sim.call("read_status", reversed_args) == e.text


def test_simulator_is_deterministic_and_stateless_for_reads():
    a, b = Simulator(S), Simulator(S)
    e = TOOL_EVENTS[0]
    first = a.call(e.tool, e.args)
    a.call("update_record", {"field": "billing.budget_usd", "value": "1"})
    assert a.call(e.tool, e.args) == first == b.call(e.tool, e.args)


def test_unknown_read_gives_stable_error_text():
    sim = Simulator(S)
    out = sim.call("read_document", {"doc_id": "D-nope"})
    assert out.startswith("ERROR") and out == sim.call("read_document", {"doc_id": "D-nope"})
    assert sim.action_log == []


def test_update_record_goes_to_action_log_and_changes_nothing():
    sim = Simulator(S)
    r1 = sim.call("update_record", {"field": "billing.budget_usd", "value": "275000"})
    r2 = sim.call("update_record", {"field": "billing.owner", "value": "Ann"})
    assert r1.startswith("OK") and r2.startswith("OK")
    assert sim.action_log == [
        {"tool": "update_record", "args": {"field": "billing.budget_usd", "value": "275000"}},
        {"tool": "update_record", "args": {"field": "billing.owner", "value": "Ann"}},
    ]
    assert Simulator(S).action_log == []


def test_entries_follow_feed_order_with_consecutive_clock():
    es = entries(S)
    events = [e for sess in S.sessions for e in sess.events]
    assert [x.id for x in es] == [e.id for e in events]
    assert [x.clock for x in es] == list(range(1, len(events) + 1))
    sessions = [sess.index for sess in S.sessions for _ in sess.events]
    assert [x.session for x in es] == sessions
    assert {x.task_id for x in es} == {"task-" + S.id}


def test_entry_kinds_source_and_trust():
    es = {x.id: x for x in entries(S)}
    for sess in S.sessions:
        for e in sess.events:
            x = es[e.id]
            assert x.text == e.text
            if e.type == "user_message":
                assert (x.kind, x.source, x.trust, x.author, x.scope) == (
                    "user_message", "user", "trusted", "user", "task")
            elif e.tool == "read_document":
                assert (x.kind, x.source, x.trust, x.author) == ("document", "document", "untrusted", "tool")
            elif e.type == "tool_data":
                assert (x.kind, x.source, x.trust) == ("tool_output", "tool", "untrusted")
            else:
                assert x.kind in ("agent_note",) and x.author == e.author and x.scope == e.scope


def test_oracle_facts_are_the_events_facts():
    facts = {f.id: f for f in S.facts}
    for x, e in zip(entries(S), [e for sess in S.sessions for e in sess.events]):
        assert [f.id for f in x.oracle_facts] == e.facts
        assert all(f == facts[f.id] for f in x.oracle_facts)


def test_note_restating_tool_data_inherits_origin_and_distrust():
    es = {x.id: x for x in entries(S)}
    checked = inherited = 0
    for sess in S.sessions:
        tool_by_fact = {fid: e for e in sess.events if e.type == "tool_data" for fid in e.facts}
        for e in sess.events:
            if e.type != "note":
                continue
            checked += 1
            src = [tool_by_fact.get(fid) for fid in e.facts]
            if e.facts and all(src) and len({x.id for x in src}) == 1:
                inherited += 1
                assert es[e.id].origin == src[0].id and es[e.id].trust == "untrusted"
            else:
                assert es[e.id].origin is None and es[e.id].trust == "agent" and es[e.id].source == "agent"
    assert checked > 5 and inherited >= 1
