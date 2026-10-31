"""Rolling summary: one digest line per session, oldest lines dropped to fit the limit."""
from __future__ import annotations

import json
from pathlib import Path

from mam.extract import make_extractor
from mam.systems.base import MemorySystem, make_context
from mam.tokens import count
from mam.types import Context, ContextItem, Reader


class RollingSummary(MemorySystem):
    """Facts found by the extractor, written as short lines and never revised or closed."""

    def __init__(self, limit: int, extractor: str, cache_path=None):
        if extractor == "oracle":
            raise ValueError("rolling_summary has no oracle extractor")
        super().__init__(limit)
        self._extractor = make_extractor(extractor, cache_path)
        self._digests: dict[int, list[str]] = {}
        self._done: set[str] = set()

    def end_session(self, session: int) -> None:
        for e in sorted(self._entries.values(), key=lambda e: e.clock):
            if e.session != session or e.id in self._done or e.scope == "private":
                continue
            self._done.add(e.id)
            lines = self._digests.setdefault(session, [])
            for f in self._extractor.extract(e).facts:
                line = f"{f.entity} {f.attribute}={f.value}"
                if line not in lines:
                    lines.append(line)

    def context(self, reader: Reader) -> Context:
        lines = [f"S{s}: " + "; ".join(ls) for s, ls in sorted(self._digests.items()) if ls]
        while lines and count("\n".join(lines)) > self.limit:
            lines.pop(0)
        if not lines:
            return make_context([])
        return make_context([ContextItem(id="summary", kind="summary", text="\n".join(lines))])


_SUMMARY_SYSTEM = ("You maintain a short running summary of a software implementation project. Given the previous "
                   "summary and the new messages of one session, write the updated summary as plain lines, newest "
                   "information included, at most {words} words. Keep concrete values (dates, amounts, names, "
                   "owners) and standing rules. Reply with the summary only.")


class _TextSummary(MemorySystem):
    """A summary kept as text; the context is its newest lines that fit the limit."""

    def __init__(self, limit: int):
        super().__init__(limit)
        self._summary = ""
        self.refusals: list[int] = []

    @property
    def summary_text(self) -> str:
        return self._summary

    def context(self, reader: Reader) -> Context:
        lines = [ln for ln in self._summary.split("\n") if ln.strip()]
        while lines and count("\n".join(lines)) > self.limit:
            lines.pop(0)
        if not lines:
            return make_context([])
        return make_context([ContextItem(id="summary", kind="summary", text="\n".join(lines))])


class LLMSummary(_TextSummary):
    """The summary baseline written by the model once per session."""

    def __init__(self, limit: int, llm):
        super().__init__(limit)
        self.llm = llm
        self._done: set[str] = set()
        self._calls: list = []

    def drain_llm_calls(self) -> list:
        calls, self._calls = self._calls, []
        return calls

    def end_session(self, session: int) -> None:
        new = [e for e in sorted(self._entries.values(), key=lambda e: e.clock)
               if e.session == session and e.id not in self._done and e.scope != "private"]
        self._done.update(e.id for e in new)
        if not new:
            return
        body = "\n".join(f"[{e.kind}] {e.text}" for e in new)
        prompt = f"PREVIOUS SUMMARY\n{self._summary or '(empty)'}\n\nNEW MESSAGES\n{body}\n\nReply with the summary only."
        out = self.llm.complete(_SUMMARY_SYSTEM.format(words=int(self.limit * 0.5)), [{"role": "user", "content": prompt}], {})
        self._calls.append(("summary", out))
        if out.refusal:
            self.refusals.append(session)
        else:
            self._summary = out.text.strip()


class CachedSummary(_TextSummary):
    """Replays the summaries the model wrote in the extraction pass (rows of kind summary)."""

    def __init__(self, limit: int, cache_path):
        super().__init__(limit)
        self._rows: dict[tuple[str, int], dict] = {}
        for line in Path(cache_path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if row.get("kind") == "summary":
                    self._rows[(row["task_id"], row["session"])] = row

    def end_session(self, session: int) -> None:
        task_ids = sorted({e.task_id for e in self._entries.values()})
        row = next((self._rows[(t, session)] for t in task_ids if (t, session) in self._rows), None)
        if row is None:
            return
        if row.get("refusal"):
            self.refusals.append(session)
        else:
            self._summary = str(row["text"]).strip()
