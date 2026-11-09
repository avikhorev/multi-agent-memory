"""Общее поведение всех систем памяти: идемпотентная запись, фильтр по области видимости, подсчёт токенов."""
from __future__ import annotations

from mam.tokens import count
from mam.types import Context, ContextItem, Entry, Reader

def visible_to(entry: Entry, reader: Reader) -> bool:
    """Фильтр области видимости. Применяется до любого ранжирования и поиска,
    чтобы закрытая запись не могла попасть в контекст чужому агенту."""
    if entry.scope == "private":
        # Личное видит только автор (по роли).
        return entry.author == reader.role
    if entry.scope == "task":
        # Запись задачи видна только в рамках этой же задачи.
        return entry.task_id == reader.task_id
    # Остальные области (общая) видны всем.
    return True

def make_context(items: list[ContextItem]) -> Context:
    """Собирает контекст и считает его размер в токенах."""
    return Context(items=items, token_count=sum(count(i.text) for i in items))

class MemorySystem:
    """Базовый класс. Записи приходят в порядке возрастания clock; повторный id записи игнорируется."""

    def __init__(self, limit: int = 2000):
        # Бюджет контекста в токенах: больше этого система не отдаёт.
        self.limit = limit
        # Все принятые записи по id; повтор не перезаписывает (запись идемпотентна).
        self._entries: dict[str, Entry] = {}

    def write(self, entry: Entry) -> None:
        if entry.id not in self._entries:
            self._entries[entry.id] = entry

    def end_session(self, session: int) -> None:
        """Хук для систем, которые извлекают факты или строят сводки в конце сессии."""

    def drain_llm_calls(self) -> list:
        """Отдаёт накопленные вызовы модели для учёта стоимости; у систем без модели их нет."""
        return []

    def drain_extractions(self) -> list[dict]:
        """Отдаёт накопленные результаты извлечения (для кеша); у систем без извлечения пусто."""
        return []

    def context(self, reader: Reader) -> Context:
        """Главный метод: что показать читателю. Реализуется в каждой системе."""
        raise NotImplementedError

    def _visible(self, reader: Reader) -> list[Entry]:
        """Записи, видимые читателю, в хронологическом порядке."""
        return sorted((e for e in self._entries.values() if visible_to(e, reader)), key=lambda e: e.clock)
