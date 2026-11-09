"""Скользящая сводка: одна строка-дайджест на сессию, самые старые строки отбрасываются, чтобы уложиться в лимит."""
from __future__ import annotations

import json
import re
from pathlib import Path

from mam.extractors import make_extractor
from mam.systems.base import MemorySystem, make_context
from mam.tokens import count
from mam.types import Context, ContextItem, Reader


class RollingSummary(MemorySystem):
    """Факты, найденные извлекателем, записываются короткими строками и никогда не пересматриваются и не закрываются.
    Поэтому устаревшее значение остаётся рядом с новым: это слабость базовой системы, которую мы и измеряем."""

    def __init__(self, limit: int, extractor: str, cache_path=None):
        if extractor == "oracle":
            raise ValueError("rolling_summary has no oracle extractor")
        super().__init__(limit)
        self._extractor = make_extractor(extractor, cache_path)
        self._digests: dict[int, list[str]] = {}  # номер сессии -> строки «сущность атрибут=значение»
        self._done: set[str] = set()  # id записей, которые уже обработаны

    def end_session(self, session: int) -> None:
        for e in sorted(self._entries.values(), key=lambda e: e.clock):
            # Чужие сессии и уже обработанное пропускаем; личные записи не попадают в общую сводку.
            if e.session != session or e.id in self._done or e.scope == "private":
                continue
            self._done.add(e.id)
            lines = self._digests.setdefault(session, [])
            for f in self._extractor.extract(e).facts:
                line = f"{f.entity} {f.attribute}={f.value}"
                if line not in lines:  # без повторов внутри сессии
                    lines.append(line)

    def context(self, reader: Reader) -> Context:
        lines = [f"S{s}: " + "; ".join(ls) for s, ls in sorted(self._digests.items()) if ls]
        # Не влезает — выбрасываем самые старые строки (они же и самые вероятно устаревшие).
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

# Командная утилита добавляет в каждый промпт блок о рабочем каталоге и работе с файлами; модель может
# скопировать его в свою сводку. Такие строки — не информация о проекте, их удаляем.
_ENVIRONMENT_LINE = re.compile(r"/tmp/|working directory|git repository|^\W*platform\W|downloaded files|run python with -i",
                               re.I)


def clean_summary(text: str) -> str:
    """Убирает из сводки строки про окружение и опустевший заголовок «Standing notes»."""
    kept = [ln for ln in text.split("\n") if not _ENVIRONMENT_LINE.search(ln)]
    out: list[str] = []
    for i, ln in enumerate(kept):
        if ln.strip().lower().rstrip(":") == "standing notes":  # заголовок, у которого удалили все пункты, тоже убираем
            following = next((x for x in kept[i + 1:] if x.strip()), "")
            if not following.lstrip().startswith("-"):
                continue
        out.append(ln)
    return "\n".join(out).strip()


class _TextSummary(MemorySystem):
    """Сводка, хранимая как текст; в контекст идут её самые новые строки, что помещаются в лимит."""

    def __init__(self, limit: int):
        super().__init__(limit)
        self._summary = ""  # текущий текст сводки
        self.refusals: list[int] = []  # номера сессий, на которых модель отказалась писать сводку

    @property  # текст сводки для чтения снаружи (кеш, отчёты)
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
    """Базовая система «сводка»: модель переписывает сводку один раз за сессию."""

    def __init__(self, limit: int, llm):
        super().__init__(limit)
        self.llm = llm  # клиент модели
        self._done: set[str] = set()  # записи, уже вошедшие в сводку
        self._calls: list = []  # вызовы модели, накопленные для учёта стоимости

    def drain_llm_calls(self) -> list:
        """Отдаёт накопленные вызовы и обнуляет список, чтобы вызов не посчитали дважды."""
        calls, self._calls = self._calls, []
        return calls

    def end_session(self, session: int) -> None:
        new = [e for e in sorted(self._entries.values(), key=lambda e: e.clock)
               if e.session == session and e.id not in self._done and e.scope != "private"]
        self._done.update(e.id for e in new)
        if not new:  # новых записей нет — модель не вызываем, экономим стоимость
            return
        body = "\n".join(f"[{e.kind}] {e.text}" for e in new)
        prompt = f"PREVIOUS SUMMARY\n{self._summary or '(empty)'}\n\nNEW MESSAGES\n{body}\n\nReply with the summary only."
        out = self.llm.complete(_SUMMARY_SYSTEM.format(words=int(self.limit * 0.5)), [{"role": "user", "content": prompt}], {})
        self._calls.append(("summary", out))
        if out.refusal:
            self.refusals.append(session)  # прежняя сводка остаётся как есть
        else:
            self._summary = clean_summary(out.text)


class CachedSummary(_TextSummary):
    """Воспроизводит сводки, которые модель написала при проходе извлечения (строки кеша вида summary).
    Так прогон памяти не обращается к модели и повторяем."""

    def __init__(self, limit: int, cache_path):
        super().__init__(limit)
        self._rows: dict[tuple[str, int], dict] = {}  # (задача, сессия) -> строка кеша
        for line in Path(cache_path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if row.get("kind") == "summary":
                    self._rows[(row["task_id"], row["session"])] = row

    def end_session(self, session: int) -> None:
        # Задача заранее неизвестна, поэтому берём её из принятых записей.
        task_ids = sorted({e.task_id for e in self._entries.values()})
        row = next((self._rows[(t, session)] for t in task_ids if (t, session) in self._rows), None)
        if row is None:
            return
        if row.get("refusal"):
            self.refusals.append(session)
        else:
            self._summary = str(row["text"]).strip()
