"""Quality of the saved extractions against the ground truth, split by kind of update."""
import json

from mam.extraction_quality import quality, render
from mam.generate import generate
from mam.scenario import dump
from mam.simulate import entries


def cache_row(task, e, facts, refusal=False):
    return {"kind": "entry", "scenario": task[5:], "task_id": task, "entry_id": e.id, "session": e.session,
            "refusal": refusal, "constraints": [],
            "facts": [{"entity": f.entity, "attribute": f.attribute, "value": f.value, "event_time": f.valid_from,
                       "source": f.source} for f in facts]}


def setup(tmp_path, miss_factor=False, refuse_one=False):
    s = generate("C1", 101, variant="implicit")
    data = tmp_path / "data"
    data.mkdir()
    dump(s, data / f"{s.id}.json")
    task = f"task-{s.id}"
    rows = []
    for e in entries(s):
        if e.kind not in ("user_message", "tool_output", "document", "draft") and not (e.kind == "agent_note" and e.id.startswith("x-")):
            continue
        facts = [] if (miss_factor and e.id.startswith("x-")) else list(e.oracle_facts)
        rows.append(cache_row(task, e, facts, refusal=refuse_one and e.id == "e-0001"))
    cache = tmp_path / "cache.jsonl"
    cache.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return s, data, cache


def test_a_perfect_cache_has_precision_and_recall_one_everywhere(tmp_path):
    s, data, cache = setup(tmp_path)
    q = quality(cache, data)
    for part in ("base", "update"):
        r = q[("implicit", part)]
        assert r["fp"] == 0 and r["fn"] == 0 and r["tp"] > 0
    assert q["_refusals"] == 0


def test_a_missed_implicit_update_lowers_recall_of_the_update_part_only(tmp_path):
    s, data, cache = setup(tmp_path, miss_factor=True)
    q = quality(cache, data)
    assert q[("implicit", "update")]["fn"] == 1 and q[("implicit", "update")]["tp"] == 0
    assert q[("implicit", "base")]["fn"] == 0


def test_refusals_are_counted_apart_and_their_facts_count_as_missed(tmp_path):
    s, data, cache = setup(tmp_path, refuse_one=True)
    q = quality(cache, data)
    assert q["_refusals"] == 1 and q[("implicit", "base")]["fn"] >= 1


def test_the_table_has_a_row_per_kind_of_update(tmp_path):
    s, data, cache = setup(tmp_path)
    text = render(quality(cache, data))
    assert "implicit" in text and "update" in text and "precision" in text and "recall" in text
