"""Graphiti for the benchmark (D42). graphiti-core 0.31.2, defaults except: the model is the benchmark client (Haiku, answers asked
as JSON of a given shape), the embedder is local fastembed (BAAI/bge-small-en-v1.5, 384 dim.), no reranker, the graph is the
embedded Kuzu in a temporary folder with full-text indexes made by the library's own queries. Records go to add_episode at
end_session in clock order, dated a base day plus the clock in days; context() keeps valid facts of episodes the reader may see."""
import asyncio, json, os, re, tempfile  # noqa: E401
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
from graphiti_core.driver.driver import GraphProvider  # noqa: E402
from graphiti_core.graph_queries import get_fulltext_indices  # noqa: E402

from mam.systems.base import MemorySystem, make_context  # noqa: E402
from mam.tokens import count  # noqa: E402
from mam.types import ContextItem  # noqa: E402

BASE_DAY = datetime(2026, 1, 1, tzinfo=timezone.utc)


def shape(s, defs):  # a placeholder instance of a JSON schema: the model copies the shape instead of echoing the schema
    s = defs[s["$ref"].split("/")[-1]] if "$ref" in s else next((x for x in s["anyOf"] if x.get("type") != "null"), {}) if "anyOf" in s else s
    t = s.get("type")
    return ({k: shape(v, defs) for k, v in s.get("properties", {}).items()} if t == "object" else [shape(s.get("items", {}), defs)] if t == "array"
            else 0 if t in ("integer", "number") else False if t == "boolean" else "...")


class ClientLLM(LLMClient):
    def __init__(self, llm, calls):
        super().__init__(LLMConfig(api_key="none", model="client"), cache=False)
        self.llm, self.calls = llm, calls

    async def _generate_response(self, messages, response_model=None, max_tokens=8192, model_size=None, **kw):
        system = "\n".join(m.content for m in messages if m.role == "system")
        if response_model:
            system += "\nReply with one JSON object only, in exactly this shape with the placeholders replaced by the answer: " + json.dumps(shape(sc := response_model.model_json_schema(), sc.get("$defs", {})))
        user = "\n".join(m.content for m in messages if m.role != "system")
        out = await asyncio.get_running_loop().run_in_executor(None, self.llm.complete, system, [{"role": "user", "content": user}], {})
        self.calls.append(("memory", out))
        m = re.search(r"\{.*\}", out.text, re.S)
        return json.loads(m.group(0)) if m and not out.refusal else {}


class Embedder(EmbedderClient):
    model = TextEmbedding("BAAI/bge-small-en-v1.5")

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
        for q in ["INSTALL fts", "LOAD EXTENSION fts", *get_fulltext_indices(GraphProvider.KUZU)]:  # the Kuzu driver builds none itself
            self.loop.run_until_complete(self.g.driver.execute_query(q))

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
        edges = self.loop.run_until_complete(self.g.search(reader.query, num_results=20))
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
