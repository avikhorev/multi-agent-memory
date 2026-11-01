"""Graphiti as a memory system of the benchmark (decision D42). graphiti-core 0.31.2 with its defaults, except: the model is
the benchmark client (Haiku through ClaudeCliClient; structured answers are asked as JSON that follows the schema), the
embedder is local fastembed (BAAI/bge-small-en-v1.5, 384 dimensions), no reranker, the graph is the embedded Kuzu in a
temporary folder, and search uses cosine similarity of facts only (this version creates no full-text indexes for Kuzu,
so the default hybrid search fails). Records go to add_episode at end_session in clock order, one episode per record, in
the default group (one graph per scenario); an episode is dated a fixed base day plus its clock in days. context()
keeps the facts that are still valid and come from episodes the reader may see."""
import asyncio
import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone

os.environ.update(EMBEDDING_DIM="384", GRAPHITI_TELEMETRY_ENABLED="false")
from fastembed import TextEmbedding  # noqa: E402
from graphiti_core import Graphiti  # noqa: E402
from graphiti_core.cross_encoder.client import CrossEncoderClient  # noqa: E402
from graphiti_core.driver.kuzu_driver import KuzuDriver  # noqa: E402
from graphiti_core.embedder.client import EmbedderClient  # noqa: E402
from graphiti_core.llm_client.client import LLMClient  # noqa: E402
from graphiti_core.llm_client.config import LLMConfig  # noqa: E402
from graphiti_core.nodes import EpisodeType  # noqa: E402
from graphiti_core.search.search_config import EdgeReranker, EdgeSearchConfig, EdgeSearchMethod, SearchConfig  # noqa: E402

from mam.systems.base import MemorySystem, make_context  # noqa: E402
from mam.tokens import count  # noqa: E402
from mam.types import ContextItem  # noqa: E402

BASE_DAY = datetime(2026, 1, 1, tzinfo=timezone.utc)
COSINE = SearchConfig(edge_config=EdgeSearchConfig(search_methods=[EdgeSearchMethod.cosine_similarity], reranker=EdgeReranker.rrf), limit=20)


class ClientLLM(LLMClient):
    def __init__(self, llm, calls):
        super().__init__(LLMConfig(api_key="none", model="client"), cache=False)
        self.llm, self.calls = llm, calls

    async def _generate_response(self, messages, response_model=None, max_tokens=8192, model_size=None, **kw):
        system = "\n".join(m.content for m in messages if m.role == "system")
        if response_model:
            system += "\nReply with one JSON object only that follows this JSON schema: " + json.dumps(response_model.model_json_schema())
        user = "\n".join(m.content for m in messages if m.role != "system")
        out = await asyncio.get_running_loop().run_in_executor(None, self.llm.complete, system, [{"role": "user", "content": user}], {})
        self.calls.append(("memory", out))
        m = re.search(r"\{.*\}", out.text, re.S)
        return json.loads(m.group(0)) if m and not out.refusal else {}


class Embedder(EmbedderClient):
    def __init__(self):
        self.model = TextEmbedding("BAAI/bge-small-en-v1.5")

    async def create(self, input_data):
        return [float(x) for x in next(iter(self.model.embed([input_data if isinstance(input_data, str) else " ".join(map(str, input_data))])))]

    async def create_batch(self, input_data_list):
        return [[float(x) for x in v] for v in self.model.embed(input_data_list)]


class Flat(CrossEncoderClient):
    async def rank(self, query, passages):
        return [(p, 1.0) for p in passages]


class Graphiti3(MemorySystem):
    def __init__(self, limit, llm):
        super().__init__(limit)
        self.calls, self._sent, self.eid, self.loop = [], set(), {}, asyncio.new_event_loop()
        db = os.path.join(tempfile.mkdtemp(prefix="graphiti-"), "kuzu.db")
        self.g = Graphiti(graph_driver=KuzuDriver(db=db), llm_client=ClientLLM(llm, self.calls), embedder=Embedder(), cross_encoder=Flat())
        self.loop.run_until_complete(self.g.build_indices_and_constraints())

    def end_session(self, session):
        for e in sorted(self._entries.values(), key=lambda e: e.clock):
            if e.session == session and e.id not in self._sent:
                self._sent.add(e.id)
                res = self.loop.run_until_complete(self.g.add_episode(
                    name=e.id, episode_body=e.text, source_description=f"{e.kind} by {e.author}", source=EpisodeType.text,
                    reference_time=BASE_DAY + timedelta(days=e.clock)))
                self.eid[res.episode.uuid] = e

    def drain_llm_calls(self):
        calls, self.calls[:] = list(self.calls), []
        return calls

    def context(self, reader):
        edges = self.loop.run_until_complete(self.g.search_(reader.query, config=COSINE)).edges
        hidden = {u for u, e in self.eid.items() if e.scope == "private" and e.author != reader.role}
        items, used = [], 0
        for ed in edges:
            if ed.invalid_at or ed.expired_at or (set(ed.episodes or []) and set(ed.episodes) <= hidden):
                continue
            if used + count(ed.fact) <= self.limit:
                items.append(ContextItem(id=f"graphiti-{ed.uuid}", kind="raw", text=ed.fact))
                used += count(ed.fact)
        return make_context(items)


create = lambda limit, llm: Graphiti3(limit, llm)  # noqa: E731
