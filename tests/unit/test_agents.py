"""Stateless agents: prompts in, one strict JSON action out."""
import json

import pytest

from mam.agents import ActionError, parse_action, run_agent
from mam.llm import FakeClient

GOOD = {"tool": "none", "args": {}, "answer": "done", "notes": ["a", "b"]}


def reply(**over):
    return json.dumps({**GOOD, **over})


def test_a_plain_json_reply_is_parsed():
    assert parse_action(reply()) == GOOD


def test_code_fences_and_surrounding_prose_are_tolerated():
    assert parse_action("Here you go:\n```json\n" + reply() + "\n```\nThanks") == GOOD


@pytest.mark.parametrize("bad", ["not json", "[1, 2]", reply(tool="delete_all"), json.dumps({"tool": "none"}),
                                 reply(args="x"), reply(notes="x"), reply(answer=5)])
def test_invalid_actions_are_rejected(bad):
    with pytest.raises(ActionError):
        parse_action(bad)


def test_more_than_three_notes_are_cut_to_three():
    assert parse_action(reply(notes=list("abcde")))["notes"] == ["a", "b", "c"]


def test_invalid_json_gets_exactly_one_retry():
    llm = FakeClient(["oops", reply()])
    res = run_agent(llm, "worker", context="CTX", task="T")
    assert res.action == GOOD and len(res.calls) == 2 and not res.refusal
    assert "not valid" in llm.calls[1]["messages"][0]["content"]


def test_two_invalid_replies_end_in_an_agent_error():
    res = run_agent(FakeClient(["oops", "still oops"]), "worker", context="CTX", task="T")
    assert res.action is None and res.error and len(res.calls) == 2


def test_a_refusal_is_retried_once_then_reported():
    both = run_agent(FakeClient(lambda s, m: None), "planner", context="C", task="T")
    assert both.refusal and both.action is None and len(both.calls) == 2
    once = run_agent(FakeClient([None, reply()]) if False else FakeClient(_refuse_then(reply())), "planner",
                     context="C", task="T")
    assert once.action == GOOD and not once.refusal and len(once.calls) == 2


def _refuse_then(text):
    seen = []

    def f(system, messages):
        seen.append(1)
        return None if len(seen) == 1 else text
    return f


def test_the_prompt_carries_context_task_sources_and_the_tool_result():
    llm = FakeClient([reply()])
    run_agent(llm, "worker", context="FACT A", task="do the thing", session=4, user_message="hello there",
              sources=["read_document {\"doc_id\": \"D-1\"} - Pack"], tool_result="DOC TEXT")
    prompt = llm.calls[0]["messages"][0]["content"]
    for part in ("FACT A", "do the thing", "hello there", "D-1", "DOC TEXT", "SESSION 4"):
        assert part in prompt


def test_each_role_has_its_own_system_prompt_with_the_output_format():
    systems = {}
    for role in ("planner", "worker", "reviewer"):
        llm = FakeClient([reply()])
        run_agent(llm, role, context="", task="t")
        systems[role] = llm.calls[0]["system"]
        assert '"notes"' in systems[role] and "JSON" in systems[role]
    assert len(set(systems.values())) == 3
    with pytest.raises(ValueError):
        run_agent(FakeClient([reply()]), "janitor", context="", task="t")
