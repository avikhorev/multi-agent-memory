"""Extractors through their public interface, with literal expectations."""
import json

from mam.extract import UNKNOWN_TIME, CacheExtractor, OracleExtractor, RulesExtractor, make_extractor
from mam.types import Entry, Fact


def entry(text, kind="user_message", trust="trusted", source="user", author="user", facts=()):
    return Entry(id="e1", clock=1, session=1, author=author, kind=kind, text=text, scope="task", source=source,
                 trust=trust, origin=None, task_id="t", oracle_facts=tuple(facts))


def triples(extraction):
    return {(f.entity, f.attribute, f.value) for f in extraction.facts}


def test_rules_read_a_plain_status_sentence():
    e = entry("Status update. For the reporting module, the handover date is 2026-11-06. A vendor demo is planned.")
    assert triples(RulesExtractor().extract(e)) == {("Atlas/reporting", "handover_date", "2026-11-06")}


def test_rules_read_a_status_feed_block():
    e = entry("STATUS Atlas/reporting\nUAT start date: 2026-10-01\nbuild: green\nopen items: 2", kind="tool_output",
              trust="untrusted", source="tool", author="worker")
    assert triples(RulesExtractor().extract(e)) == {("Atlas/reporting", "uat_start_date", "2026-10-01")}


def test_rules_normalise_money_and_counts():
    money = entry("Reviewer note: Noted contingency reserve for the search module: USD 388,000.", kind="agent_note",
                  trust="agent", source="agent", author="reviewer")
    count = entry("For the search module, the pilot user count is 19,000.")
    assert triples(RulesExtractor().extract(money)) == {("Atlas/search", "contingency_usd", "388000")}
    assert triples(RulesExtractor().extract(count)) == {("Atlas/search", "user_count", "19000")}


def test_rules_use_the_stated_event_time_and_source():
    e = entry("Planner note: the sign-off date for the search module is 2026-07-19 (per the status feed, as of 2026-01-20).",
              kind="agent_note", trust="agent", source="agent", author="planner")
    (fact,) = RulesExtractor().extract(e).facts
    assert (fact.value, fact.valid_from, fact.source) == ("2026-07-19", 15, "tool")


def test_rules_miss_an_implicit_update():
    e = entry("Finance trimmed what we agreed to spend on the analytics module by 25 percent.")
    assert RulesExtractor().extract(e).facts == ()


def test_fact_without_stated_time_is_marked_unknown():
    e = entry("The tech lead for the Atlas project is Pavel Dubois.")
    (fact,) = RulesExtractor().extract(e).facts
    assert (fact.entity, fact.value, fact.valid_from) == ("Atlas", "Pavel Dubois", UNKNOWN_TIME)


def test_constraints_come_only_from_trusted_text_in_every_variant():
    rule = "Hard rule from now on: never edit the archive.uat_start_date field in the project record."
    trusted, untrusted = entry(rule), entry(rule, kind="document", trust="untrusted", source="document")
    for ex in (OracleExtractor(), RulesExtractor()):
        assert ex.extract(trusted).constraints == (rule,)
        assert ex.extract(untrusted).constraints == ()


def test_oracle_returns_the_facts_given_with_the_entry():
    f = Fact("f1", "Atlas", "owner", "Yara Rossi", 3, None, None, "user")
    assert OracleExtractor().extract(entry("anything", facts=[f])).facts == (f,)


def test_cache_replays_facts_refusals_and_misses(tmp_path):
    path = tmp_path / "cache.jsonl"
    rows = [
        {"entry_id": "e1", "facts": [{"entity": "Atlas", "attribute": "owner", "value": "Yara Rossi",
                                      "event_time": 4, "source": "user"}], "constraints": ["never do x"]},
        {"entry_id": "e2", "refusal": True},
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows))
    cache = CacheExtractor(path)
    got = cache.extract(entry("text"))
    assert triples(got) == {("Atlas", "owner", "Yara Rossi")} and got.constraints == ("never do x",)
    refused = cache.extract(Entry(**{**entry("t").__dict__, "id": "e2"}))
    assert refused.refused and refused.facts == ()
    assert cache.extract(Entry(**{**entry("t").__dict__, "id": "e3"})).facts == ()


def test_unknown_extractor_and_missing_cache_path_are_rejected():
    import pytest
    with pytest.raises(ValueError):
        make_extractor("magic")
    with pytest.raises(ValueError):
        make_extractor("cache")
