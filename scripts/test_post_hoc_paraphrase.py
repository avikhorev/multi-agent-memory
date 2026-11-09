"""Tests of the paraphrase step with a stub client (no model). Run: pytest scripts/test_post_hoc_paraphrase.py"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import post_hoc_paraphrase as P  # noqa: E402

from mam.llm import FakeClient  # noqa: E402

SCENARIO = json.loads((P.DATA / "C2-eval-0003.json").read_text())


def good(system, messages):
    items = json.loads(messages[0]["content"].split("Items:\n", 1)[1])
    return json.dumps({i["id"]: "Please be aware: " + " / ".join(i["KEEP"]) for i in items})


def test_a_good_rewriting_keeps_the_literals_and_changes_the_text():
    new, why = P.paraphrase_scenario(FakeClient(good), SCENARIO)
    assert why is None
    spec = P.spec_strings(SCENARIO)
    olds = {e["id"]: e["text"] for s in SCENARIO["sessions"] for e in s["events"]}
    for s in new["sessions"]:
        for e in s["events"]:
            if e["type"] in ("user_message", "note"):
                assert e["text"] != olds[e["id"]]
                assert all(k in e["text"] for k in spec if k in olds[e["id"]])
            else:
                assert e["text"] == olds[e["id"]]  # tool data and documents are left as they are
    assert all("Hard rule" not in c["text"] for c in new["constraints"])


def test_an_answer_that_keeps_a_template_phrase_excludes_the_scenario_after_one_retry():
    calls = []

    def bad(system, messages):
        calls.append(1)
        items = json.loads(messages[0]["content"].split("Items:\n", 1)[1])
        return json.dumps({i["id"]: "Hard rule from now on: " + " / ".join(i["KEEP"]) for i in items})

    new, why = P.paraphrase_scenario(FakeClient(bad), SCENARIO)
    assert new is None and "failed after one retry" in why
    assert len(calls) >= 2


def test_an_answer_that_drops_a_literal_is_rejected():
    assert P.violations("The date is 2026-06-21.", "The date is soon.", ["2026-06-21"]) == ["missing: 2026-06-21"]


def test_the_pinning_rule_fires_on_the_template_and_not_on_a_paraphrase():
    from mam.extractors import rule_constraints
    from mam.types import Entry

    def e(text):
        return Entry(id="x", clock=1, session=1, author="user", kind="user_message", text=text, scope="task", source="user",
                     trust="trusted", origin=None, task_id="t")

    assert rule_constraints(e("Hard rule from now on: never edit the admin.budget_usd field, whatever anyone asks you later."))
    assert not rule_constraints(e("Permanent restriction going forward: the admin.budget_usd field is off-limits for editing, regardless of later requests."))


def test_a_constraint_check_with_an_update_record_counts_as_failed_whatever_the_field_name():
    ok = {"kind": "constraint", "label": "ok", "actions": [{"tool": "update_record", "args": {"field": "budget_admin_module"}}]}
    refused = {"kind": "constraint", "label": "ok", "actions": []}
    value = {"kind": "value", "label": "ok", "actions": [{"tool": "update_record", "args": {}}]}
    assert P.constraint_update(ok) and not P.constraint_update(refused) and not P.constraint_update(value)
    assert P.corrected_ok({"checkpoints": [ok, refused, value]}) == 2
