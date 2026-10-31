"""Extraction by the model, and the model-written summary, with scripted replies."""
import json

from mam.extract import LLMExtractor, UNKNOWN_TIME
from mam.llm import FakeClient
from mam.systems import create
from mam.types import Entry, Reader


def entry(i, text, kind="user_message", author="user", trust="trusted", session=1):
    return Entry(id=i, clock=int(i[1:]) if i[1:].isdigit() else 1, session=session, author=author, kind=kind, text=text,
                 scope="task", source="user", trust=trust, origin=None, task_id="t")


def facts_json(*rows):
    return json.dumps({"facts": list(rows)})


ROW = {"entity": "Atlas/billing", "attribute": "budget_usd", "value": "USD 281,000", "as_of": "2026-02-03"}


def test_facts_are_parsed_normalised_and_dated():
    ex = LLMExtractor(FakeClient([facts_json(ROW)])).extract(entry("e1", "text"))
    (f,) = ex.facts
    assert (f.entity, f.attribute, f.value, f.valid_from, f.source) == ("Atlas/billing", "budget_usd", "281000", 29, "user")


def test_missing_date_is_unknown_and_foreign_attributes_are_skipped():
    row2 = dict(ROW, attribute="favourite_colour")
    ex = LLMExtractor(FakeClient([facts_json(dict(ROW, as_of=None), row2)])).extract(entry("e1", "text"))
    assert [f.attribute for f in ex.facts] == ["budget_usd"] and ex.facts[0].valid_from == UNKNOWN_TIME


def test_known_facts_and_the_message_go_into_the_prompt():
    llm = FakeClient([facts_json()])
    LLMExtractor(llm).extract(entry("e1", "trimmed by 25 percent"), known=["Atlas/billing budget_usd = 281000"])
    prompt = llm.calls[0]["messages"][0]["content"]
    assert "281000" in prompt and "trimmed by 25 percent" in prompt


def test_a_repeated_refusal_is_flagged_and_a_single_one_is_retried():
    twice = LLMExtractor(FakeClient(lambda s, m: None)).extract(entry("e1", "text"))
    assert twice.refused and twice.facts == ()
    seen = []
    once = LLMExtractor(FakeClient(lambda s, m: (seen.append(1), None if len(seen) == 1 else facts_json(ROW))[1]))
    assert not once.extract(entry("e1", "text")).refused and len(seen) == 2


def test_unparseable_replies_give_nothing_after_one_retry():
    ex = LLMExtractor(FakeClient(["oops", "oops again"]))
    assert ex.extract(entry("e1", "text")).facts == () and ex.parse_errors == 2


def test_only_sources_of_facts_are_sent_to_the_model():
    llm = FakeClient([facts_json()])
    ex = LLMExtractor(llm)
    ex.extract(entry("n-1", "Worker note: repeats a fact", kind="agent_note", author="worker", trust="agent"))
    assert llm.calls == []
    ex.extract(entry("x-1", "Planner note: scripted conflict", kind="agent_note", author="planner", trust="agent"))
    assert len(llm.calls) == 1


def test_constraints_come_from_the_rule_even_when_the_model_refuses():
    rule = "Hard rule from now on: never edit the budget field."
    ex = LLMExtractor(FakeClient(lambda s, m: None)).extract(entry("e1", rule))
    assert ex.refused and ex.constraints == (rule,)


def test_the_structured_memory_uses_model_facts_and_hands_the_earlier_ones_to_the_next_call():
    llm = FakeClient([facts_json(dict(ROW, as_of=None)),
                      facts_json(dict(ROW, value="210750", as_of=None))])
    s = create("ours", extractor="llm", llm=llm)
    s.write(entry("e1", "The budget for the billing module is USD 281,000.", session=1))
    s.end_session(1)
    s.write(entry("e2", "Finance trimmed the billing budget by 25 percent.", session=2))
    s.end_session(2)
    assert "281000" in llm.calls[1]["messages"][0]["content"]
    ctx = s.context(Reader("planner", "t", 3, "billing budget"))
    assert "210750" in ctx.render() and "281000" not in ctx.render()
    assert len(s.drain_llm_calls()) == 2 and s.drain_llm_calls() == []


def test_the_model_written_summary_replaces_the_old_one_and_a_refusal_keeps_it():
    llm = FakeClient(["billing budget is 281000", None, None])
    s = create("rolling_summary", extractor="llm", llm=llm)
    s.write(entry("e1", "The budget is USD 281,000.", session=1))
    s.end_session(1)
    s.write(entry("e2", "Something else happened.", session=2))
    s.end_session(2)
    assert "billing budget is 281000" in s.context(Reader("planner", "t", 3, "q")).render()
    assert s.refusals == [2]


def test_extractor_llm_needs_a_client():
    import pytest
    with pytest.raises(ValueError):
        create("ours", extractor="llm")
    with pytest.raises(ValueError):
        create("rolling_summary", extractor="llm")
