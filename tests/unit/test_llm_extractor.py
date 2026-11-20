"""Extraction by the model, and the model-written summary, with scripted replies."""
import json

from mam.extractors import LLMExtractor, UNKNOWN_TIME
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
    ex = LLMExtractor(FakeClient([facts_json(ROW)])).extract(entry("e1", "Budget as of 2026-02-03 is USD 281,000."))
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
    llm2 = FakeClient([facts_json()])
    LLMExtractor(llm2).extract(entry("x-2", "Private draft with a figure", kind="draft", author="worker", trust="agent"))
    assert len(llm2.calls) == 1  # drafts carry facts too; their scope keeps them from other roles


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


def test_every_extraction_is_logged_with_its_facts_and_refusal_state():
    ex = LLMExtractor(FakeClient([facts_json(ROW), None, None]))
    ex.extract(entry("e1", "Budget as of 2026-02-03 is USD 281,000."))
    ex.extract(entry("e2", "text"))
    log = ex.drain_log()
    assert [l["entry_id"] for l in log] == ["e1", "e2"]
    assert log[0]["facts"] == [{"entity": "Atlas/billing", "attribute": "budget_usd", "value": "281000",
                                "valid_from": 29, "source": "user"}] and not log[0]["refused"]
    assert log[1]["refused"] and log[1]["facts"] == []
    assert ex.drain_log() == []


def test_a_date_the_model_invents_is_ignored_unless_the_message_contains_it():
    invented = dict(ROW, as_of="2026-10-31")  # today's date, not written in the message
    ex = LLMExtractor(FakeClient([facts_json(invented)])).extract(entry("e1", "Selma Berg is now the tech lead."))
    assert ex.facts[0].valid_from == UNKNOWN_TIME
    stated = LLMExtractor(FakeClient([facts_json(ROW)])).extract(entry("e2", "Budget as of 2026-02-03 is USD 281,000."))
    assert stated.facts[0].valid_from == 29


def test_a_date_written_in_another_format_still_counts():
    row = dict(ROW, as_of="2026-02-03")
    ex = LLMExtractor(FakeClient([facts_json(row)])).extract(entry("e1", "Decided on 3 February 2026: budget USD 281,000."))
    assert ex.facts[0].valid_from == 29


def test_a_null_value_is_not_a_fact():
    rows = [dict(ROW, value=None), dict(ROW, value=""), dict(ROW, value="  "), dict(ROW, value="100", as_of=None)]
    ex = LLMExtractor(FakeClient([facts_json(*rows)])).extract(entry("e1", "text"))
    assert [f.value for f in ex.facts] == ["100"]  # JSON null must not become the text "None"


ENV_NOISE = ("billing budget is 281000\n\nStanding notes:\n"
             "- Environment: /tmp/work-a, Linux, bash, not a git repository.\n"
             "- Working directory: the previous summary lists /tmp/work-b, but the current block lists /tmp/work-c.\n"
             "- Untrusted downloaded files go in their own empty directories; run Python with -I.\n"
             "- Platform: linux\n"
             "Owner of billing is Yara Rossi")


def test_notes_about_the_working_environment_are_removed_from_a_model_summary():
    llm = FakeClient([ENV_NOISE])
    s = create("rolling_summary", extractor="llm", llm=llm)
    s.write(entry("e1", "The budget is USD 281,000.", session=1))
    s.end_session(1)
    text = s.context(Reader("planner", "t", 2, "q")).render()
    assert text == "billing budget is 281000\nOwner of billing is Yara Rossi"
    assert "/tmp/" not in s.summary_text and "Standing notes" not in s.summary_text


def test_a_standing_rule_that_is_project_information_is_kept():
    llm = FakeClient(["Standing rule: never edit the billing.budget field.\nbilling budget is 281000"])
    s = create("rolling_summary", extractor="llm", llm=llm)
    s.write(entry("e1", "The budget is USD 281,000.", session=1))
    s.end_session(1)
    assert "Standing rule: never edit the billing.budget field." in s.summary_text


def test_the_summary_prompt_tells_the_model_to_leave_the_environment_out():
    llm = FakeClient(["ok"])
    s = create("rolling_summary", extractor="llm", llm=llm)
    s.write(entry("e1", "text", session=1))
    s.end_session(1)
    system = llm.calls[0]["system"].lower()
    assert "working directory" in system and "only project information" in system
