"""Smoke test of the Graphiti adapter with a stub model. Run:
EMBEDDING_DIM=384 PYTHONPATH=src:external external/.venv-graphiti/bin/python -m pytest external/test_graphiti_smoke.py -q
"""
import json

import pytest

pytest.importorskip("mam")
from mam.llm import FakeClient  # noqa: E402
from mam.types import Entry, Reader  # noqa: E402

from graphiti_adapter import Graphiti3  # noqa: E402


def stub(system, messages):
    """An empty but valid answer for the schema that the adapter puts into the prompt."""
    schema = json.loads(system.split("follows this JSON schema: ", 1)[1]) if "JSON schema" in system else {}
    return json.dumps({k: [] if schema["properties"][k].get("type") == "array" else "" for k in schema.get("required", [])})


def entry(i, text, scope="task", author="user"):
    return Entry(id=f"e{i}", clock=i, session=1, author=author, kind="user_message", text=text, scope=scope,
                 source="user", trust="trusted", origin=None, task_id="t1")


def test_the_adapter_writes_episodes_and_reads_without_error_and_within_the_limit():
    s = Graphiti3(2000, llm=FakeClient(stub))
    s.write(entry(1, "The billing budget is 123000 dollars."))
    s.write(entry(2, "SECRET private estimate of the worker.", scope="private", author="worker"))
    s.end_session(1)
    ctx = s.context(Reader(role="planner", task_id="t1", session=2, query="billing budget"))
    assert ctx.token_count <= 2000 and not any("SECRET" in i.text for i in ctx.items)
    assert s.drain_llm_calls()
