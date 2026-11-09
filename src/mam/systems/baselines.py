"""Простые базовые системы: вся история, скользящее окно и поиск BM25 по всем видимым записям."""
from __future__ import annotations

from mam.systems.base import MemorySystem, make_context
from mam.systems.ranking import bm25_scores
from mam.tokens import count
from mam.types import Context, ContextItem, Entry, Reader

def _raw(entry: Entry) -> ContextItem:
    """Запись как есть, без обработки: kind="raw", текст не меняется."""
    return ContextItem(id=f"raw-{entry.id}", kind="raw", text=entry.text, entry_ids=(entry.id,))

class FullHistory(MemorySystem):
    """Всё видимое, по порядку. Лимита нет, ничего не обрезается (верхняя граница по полноте, но не по бюджету)."""

    def context(self, reader: Reader) -> Context:
        return make_context([_raw(e) for e in self._visible(reader)])

class SlidingWindow(MemorySystem):
    """Самые свежие видимые записи, которые помещаются в лимит, в хронологическом порядке."""

    def context(self, reader: Reader) -> Context:
        kept: list[ContextItem] = []
        used = 0
        # Идём от новых к старым и останавливаемся на первой, что не влезла:
        # окно должно быть непрерывным куском истории, без дыр.
        for e in reversed(self._visible(reader)):
            cost = count(e.text)
            if used + cost > self.limit:
                break
            kept.append(_raw(e))
            used += cost
        kept.reverse()  # возвращаем хронологический порядок
        return make_context(kept)

class SharedRagBm25(MemorySystem):
    """BM25 по видимым записям; лучшие совпадения первыми, пока лимит не заполнен."""

    def context(self, reader: Reader) -> Context:
        docs = self._visible(reader)
        scores = bm25_scores(reader.query, [d.text for d in docs])
        scored = list(zip(scores, docs))
        # При равной оценке более свежая запись идёт раньше.
        scored.sort(key=lambda p: (-p[0], -p[1].clock))
        kept, used = [], 0
        for score, d in scored:
            cost = count(d.text)
            # В отличие от окна, слишком большую запись пропускаем, а не останавливаемся:
            # дальше может найтись более короткая и всё ещё релевантная.
            if used + cost <= self.limit:
                kept.append(_raw(d))
                used += cost
        return make_context(kept)
