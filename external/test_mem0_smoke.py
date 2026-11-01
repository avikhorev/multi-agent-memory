"""Smoke test of the Mem0 adapter with a stub model (no key, no network except the embedding model download).
Run: PYTHONPATH=src:external external/.venv-mem0/bin/python -m pytest external/test_mem0_smoke.py -q
"""
import json

import pytest

mam = pytest.importorskip("mam")
from mam.llm import FakeClient  # noqa: E402
from mam.types import Entry, Reader  # noqa: E402

from mem0_adapter import Mem0  # noqa: E402


def entry(i, text, scope="task", author="user"):
    return Entry(id=f"e{i}", clock=i, session=1, author=author, kind="user_message", text=text, scope=scope,
                 source="user", trust="trusted", origin=None, task_id="t1")


def test_a_written_record_comes_back_and_a_foreign_private_one_does_not():
    llm = FakeClient(lambda system, messages: json.dumps({"memory": [{"text": messages[0]["content"][-60:]}]}))
    s = Mem0(2000, llm=llm)
    s.write(entry(1, "The billing budget is 123000 dollars."))
    s.write(entry(2, "SECRET private estimate of the worker.", scope="private", author="worker"))
    s.end_session(1)
    ctx = s.context(Reader(role="planner", task_id="t1", session=2, query="billing budget"))
    assert ctx.items and ctx.token_count <= 2000
    assert not any("SECRET" in i.text for i in ctx.items)
    assert s.drain_llm_calls()
