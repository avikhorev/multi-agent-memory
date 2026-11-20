"""Sliding summary: one digest line per session; the oldest lines are dropped to fit the limit."""
from __future__ import annotations

import json
import re
from pathlib import Path

from mam.extract import make_extractor
from mam.systems.base import MemorySystem, make_context
from mam.tokens import count
from mam.types import Context, ContextItem, Reader


class RollingSummary(MemorySystem):
    """Facts found by the extractor are written as short lines and are never revised or closed.
    So a stale value stays next to the new one: this is a weakness of the baseline system, which is exactly what we measure."""

    def __init__(self, limit: int, extractor: str, cache_path=None):
        if extractor == "oracle":
            raise ValueError("rolling_summary has no oracle extractor")
        super().__init__(limit)
        self._extractor = make_extractor(extractor, cache_path)
        self._digests: dict[int, list[str]] = {}  # session number -> lines "entity attribute=value"
        self._done: set[str] = set()  # ids of entries already processed

    def end_session(self, session: int) -> None:
        for e in sorted(self._entries.values(), key=lambda e: e.clock):
            # Other sessions and already processed entries are skipped; personal entries do not get into the shared summary.
            if e.session != session or e.id in self._done or e.scope == "private":
                continue
            self._done.add(e.id)
            lines = self._digests.setdefault(session, [])
            for f in self._extractor.extract(e).facts:
                line = f"{f.entity} {f.attribute}={f.value}"
                if line not in lines:  # no repeats within a session
                    lines.append(line)

    def context(self, reader: Reader) -> Context:
        lines = [f"S{s}: " + "; ".join(ls) for s, ls in sorted(self._digests.items()) if ls]
        # It does not fit — drop the oldest lines (they are also the most likely to be stale).
        while lines and count("\n".join(lines)) > self.limit:
            lines.pop(0)
        if not lines:
            return make_context([])
        return make_context([ContextItem(id="summary", kind="summary", text="\n".join(lines))])


_SUMMARY_SYSTEM = ("You maintain a short running summary of a software implementation project. Given the previous "
                   "summary and the new messages of one session, write the updated summary as plain lines, newest "
                   "information included, at most {words} words. Keep concrete values (dates, amounts, names, "
                   "owners) and standing rules. Write only project information: no notes about your working directory, "
                   "platform, tools or file handling. Reply with the summary only.")

# A command-line tool adds a block about the working directory and file handling to every prompt; the model may
# copy it into its summary. Such lines are not information about the project, so we remove them.
_ENVIRONMENT_LINE = re.compile(r"/tmp/|working directory|git repository|^\W*platform\W|downloaded files|run python with -i",
                               re.I)


def clean_summary(text: str) -> str:
    """Removes from the summary the lines about the environment and the emptied "Standing notes" heading."""
    kept = [ln for ln in text.split("\n") if not _ENVIRONMENT_LINE.search(ln)]
    out: list[str] = []
    for i, ln in enumerate(kept):
        if ln.strip().lower().rstrip(":") == "standing notes":  # a heading whose items were all removed is removed too
            following = next((x for x in kept[i + 1:] if x.strip()), "")
            if not following.lstrip().startswith("-"):
                continue
        out.append(ln)
    return "\n".join(out).strip()


class _TextSummary(MemorySystem):
    """Summary stored as text; the newest of its lines that fit the limit go into the context."""

    def __init__(self, limit: int):
        super().__init__(limit)
        self._summary = ""  # current text of the summary
        self.refusals: list[int] = []  # session numbers at which the model refused to write a summary

    @property  # text of the summary for reading from outside (cache, reports)
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
    """Baseline "summary" system: the model rewrites the summary once per session."""

    def __init__(self, limit: int, llm):
        super().__init__(limit)
        self.llm = llm  # model client
        self._done: set[str] = set()  # entries already included in the summary
        self._calls: list = []  # model calls accumulated for cost accounting

    def drain_llm_calls(self) -> list:
        """Returns the accumulated calls and clears the list, so that a call is not counted twice."""
        calls, self._calls = self._calls, []
        return calls

    def end_session(self, session: int) -> None:
        new = [e for e in sorted(self._entries.values(), key=lambda e: e.clock)
               if e.session == session and e.id not in self._done and e.scope != "private"]
        self._done.update(e.id for e in new)
        if not new:  # no new entries — the model is not called, which saves cost
            return
        body = "\n".join(f"[{e.kind}] {e.text}" for e in new)
        prompt = f"PREVIOUS SUMMARY\n{self._summary or '(empty)'}\n\nNEW MESSAGES\n{body}\n\nReply with the summary only."
        out = self.llm.complete(_SUMMARY_SYSTEM.format(words=int(self.limit * 0.5)), [{"role": "user", "content": prompt}], {})
        self._calls.append(("summary", out))
        if out.refusal:
            self.refusals.append(session)  # the previous summary stays as it is
        else:
            self._summary = clean_summary(out.text)


class CachedSummary(_TextSummary):
    """Replays the summaries that the model wrote during the extraction pass (cache lines of kind summary).
    So the memory run does not call the model and is repeatable."""

    def __init__(self, limit: int, cache_path):
        super().__init__(limit)
        self._rows: dict[tuple[str, int], dict] = {}  # (task, session) -> cache line
        for line in Path(cache_path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if row.get("kind") == "summary":
                    self._rows[(row["task_id"], row["session"])] = row

    def end_session(self, session: int) -> None:
        # The task is not known in advance, so it is taken from the accepted entries.
        task_ids = sorted({e.task_id for e in self._entries.values()})
        row = next((self._rows[(t, session)] for t in task_ids if (t, session) in self._rows), None)
        if row is None:
            return
        if row.get("refusal"):
            self.refusals.append(session)
        else:
            self._summary = str(row["text"]).strip()
