"""Mem0 as a memory system of the benchmark (decision D42). Library 2.2.1 with its defaults, except:
the model is the benchmark client (Haiku through ClaudeCliClient), the embedder is local fastembed
(BAAI/bge-small-en-v1.5, 384 dimensions) and the stores are local (Qdrant in a temporary folder, SQLite history).
Mem0 gets the records at end_session, one add() per (scope, author) group of the session; add() runs one model call
and, in this version, only adds memories (event ADD); there is no update or delete in that path.
"""
import os
import tempfile

os.environ["MEM0_TELEMETRY"] = "False"
from mem0 import Memory  # noqa: E402

from mam.systems.base import MemorySystem, make_context  # noqa: E402
from mam.tokens import count  # noqa: E402
from mam.types import ContextItem  # noqa: E402


class ClientLLM:
    """The model object of Mem0, answering through the benchmark client; every call is kept for the cost record."""

    def __init__(self, llm, calls):
        self.llm, self.calls = llm, calls

    def generate_response(self, messages, response_format=None, tools=None, tool_choice="auto", **kw):
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        out = self.llm.complete(system, [{"role": "user", "content": messages[-1]["content"]}], {})
        self.calls.append(("memory", out))
        return "" if out.refusal else out.text


class Mem0(MemorySystem):
    def __init__(self, limit, llm):
        super().__init__(limit)
        self.calls, self._sent, tmp = [], set(), tempfile.mkdtemp(prefix="mem0-")
        self.m = Memory.from_config({
            "llm": {"provider": "vllm", "config": {}},  # replaced below; this provider needs no key and makes no call
            "embedder": {"provider": "fastembed", "config": {"model": "BAAI/bge-small-en-v1.5"}},
            "vector_store": {"provider": "qdrant", "config": {"path": tmp, "embedding_model_dims": 384, "on_disk": True}},
            "history_db_path": os.path.join(tmp, "history.db")})
        self.m.llm = ClientLLM(llm, self.calls)

    def end_session(self, session):
        groups = {}
        for e in sorted(self._entries.values(), key=lambda e: e.clock):
            if e.session == session and e.id not in self._sent:
                groups.setdefault((e.task_id, e.scope, e.author), []).append(e)
                self._sent.add(e.id)
        for (task, scope, author), es in groups.items():
            self.m.add([{"role": "user", "content": e.text} for e in es], user_id=task,
                       metadata={"scope": scope, "author": author, "task_id": task})

    def drain_llm_calls(self):
        calls, self.calls[:] = list(self.calls), []
        return calls

    def context(self, reader):
        hits = self.m.search(reader.query, filters={"user_id": reader.task_id}, top_k=20, threshold=0.0)["results"]
        items, used = [], 0
        for h in hits:
            md = h.get("metadata") or {}
            if md.get("scope") == "private" and md.get("author") != reader.role:
                continue
            if used + count(h["memory"]) <= self.limit:
                items.append(ContextItem(id=f"mem0-{h['id']}", kind="raw", text=h["memory"]))
                used += count(h["memory"])
        return make_context(items)


create = lambda limit, llm: Mem0(limit, llm)  # noqa: E731
