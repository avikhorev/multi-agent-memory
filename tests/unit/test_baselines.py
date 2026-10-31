"""Behaviour of the simple baselines through the public memory interface."""
from mam.systems import create
from mam.types import Entry, Reader

READER = Reader(role="planner", task_id="t1", session=3, query="what is the budget for billing")


def entry(i, text, scope="task", author="user"):
    return Entry(id=f"e{i}", clock=i, session=1, author=author, kind="user_message", text=text, scope=scope,
                 source="user", trust="trusted", origin=None, task_id="t1")


def feed(system, texts):
    for i, t in enumerate(texts, start=1):
        system.write(entry(i, t))


def test_sliding_window_keeps_the_newest_entries_in_order():
    s = create("sliding_window", limit=30)
    feed(s, [f"note number {i} with some filler words here" for i in range(1, 8)])
    texts = [i.text for i in s.context(READER).items]
    assert texts and texts[-1].startswith("note number 7")
    assert texts == sorted(texts)  # chronological, so numbers ascend
    assert not any(t.startswith("note number 1 ") for t in texts)


def test_bm25_puts_the_matching_entry_first():
    s = create("shared_rag_bm25", limit=2000)
    feed(s, ["the weather was fine", "billing budget is USD 12,000", "lunch was served at noon"])
    first = s.context(READER).items[0]
    assert "billing budget" in first.text


def test_scope_task_is_hidden_from_other_tasks():
    s = create("full_history")
    s.write(entry(1, "visible"))
    other = Reader(role="planner", task_id="other-task", session=3, query="")
    assert [i.text for i in s.context(other).items] == []
