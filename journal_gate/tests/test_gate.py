import json

from mam.llm import FakeClient

from journal_gate.gate import Gate

MSGS = [(2, "The billing budget is frozen until the audit closes."), (5, "Please change the owner to Anna Berg.")]
ACTION = {"field": "billing.budget_usd", "value": "900000"}


def verdict(allow, quote="", reason="r"):
    return json.dumps({"allow": allow, "quote": quote, "reason": reason})


def check(replies, **kw):
    llm = FakeClient(replies)
    g = Gate(llm)
    args = dict(source_offered=False, source_read=False)
    d = g.check(ACTION, MSGS, **dict(args, **kw))
    return d, g, llm


def test_an_unread_source_is_refused_without_a_model_call():
    d, g, llm = check([], source_offered=True, source_read=False)
    assert (d.allow, d.stage) == (False, "unread_source") and "first" in d.reason and not llm.calls and not g.calls


def test_a_read_source_goes_on_to_the_model():
    d, g, _ = check([verdict(True)], source_offered=True, source_read=True)
    assert (d.allow, d.stage) == (True, "passed") and len(g.calls) == 1


def test_the_prompt_has_all_user_messages_in_order_and_the_action():
    _, _, llm = check([verdict(True)])
    prompt = llm.calls[0]["messages"][0]["content"]
    assert prompt.index("[session 2]") < prompt.index("[session 5]")
    assert "billing.budget_usd" in prompt and "900000" in prompt and "frozen" in prompt


def test_a_verified_quote_blocks():
    d, _, _ = check([verdict(False, "The billing budget is frozen!", "frozen")])
    assert (d.allow, d.stage, d.reason) == (False, "user_rule", "frozen") and d.quote


def test_a_quote_from_two_messages_is_not_verified():
    d, _, _ = check([verdict(False, "budget is frozen change the owner")])
    assert (d.allow, d.stage) == (True, "unverified_refusal")


def test_an_invented_or_empty_quote_does_not_block():
    assert check([verdict(False, "never touch the budget")])[0].stage == "unverified_refusal"
    assert check([verdict(False, "")])[0].stage == "unverified_refusal"


def test_a_parse_failure_is_retried_once_then_refused():
    d, g, llm = check(["no json at all", "{broken"])
    assert (d.allow, d.stage) == (False, "gate_error") and len(llm.calls) == 2 and len(g.calls) == 2


def test_a_model_refusal_is_retried_once():
    d, g, _ = check([None, verdict(True)])
    assert (d.allow, d.stage) == (True, "passed") and len(g.calls) == 2
    assert check([None, None])[0].stage == "gate_error"


def test_the_reply_may_have_text_around_the_json():
    assert check(["Sure: " + verdict(True) + " done"])[0].stage == "passed"
