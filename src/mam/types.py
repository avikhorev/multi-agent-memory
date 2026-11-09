"""Общие типы (разделы 5 и 8 спецификации): факт, запись памяти, читатель, элемент и контекст."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Fact:
    """Атомарное утверждение о мире: «у сущности E поле A имеет значение V в период [from, to)».
    Пара (entity, attribute) — ключ, по которому разные версии одного факта сравниваются."""
    id: str  # факты сценария: "fa-NNNN" для базовых фактов, "fx-NNNN" для фактов фактора
    entity: str  # о чём факт, например "Atlas/admin"
    attribute: str  # поле, например "handover_date"
    value: str  # значение поля в виде строки
    valid_from: int  # номер дня, с которого факт начинает действовать; экстракторы могут использовать UNKNOWN_TIME (-1), если время неизвестно
    valid_to: int | None  # номер дня, когда факт перестаёт действовать; None — действует до сих пор
    supersedes: str | None  # id факта, который этот факт заменяет (обновление); None для первой версии
    source: str  # кто сообщил: user | tool | document | agent (от этого зависит авторитет)


@dataclass(frozen=True)
class Entry:
    """Одна запись, поступающая в память: сообщение, заметка, вывод инструмента и т. п.
    Неизменяема (frozen), чтобы запись нельзя было подменить после того, как её приняла память."""
    id: str  # уникальный id записи (совпадает с id события сценария); по нему запись пишется идемпотентно
    clock: int  # логические часы: порядок поступления, растёт на 1 с каждой записью
    session: int  # номер сессии, в которой запись появилась
    author: str  # роль-автор: user | planner | worker | reviewer | tool; нужен для приватности
    kind: str  # вид записи: user_message | agent_note | tool_output | document | draft
    text: str  # исходный текст записи
    scope: str  # область видимости: private (только автор) | task (в рамках задачи) | shared (всем)
    source: str  # откуда содержимое: user | agent | tool | document
    trust: str  # степень доверия: trusted | agent | untrusted (недоверенное — это данные, а не команды)
    origin: str | None  # id исходной записи, если это пересказ недоверенного источника; иначе None
    task_id: str  # задача, к которой относится запись (для области task)
    oracle_facts: tuple[Fact, ...] = ()  # эталонные факты записи из сценария; используются экстрактором «oracle» и для оценки


@dataclass(frozen=True)
class Reader:
    """Кто и с каким вопросом запрашивает контекст у памяти."""
    role: str  # роль читателя: planner | worker | reviewer (определяет, какие личные записи он видит)
    task_id: str  # текущая задача (определяет, какие записи области task видны)
    session: int  # номер текущей сессии
    query: str  # вопрос/задача, по которой ранжируются записи


@dataclass(frozen=True)
class ContextItem:
    """Один кусок готового контекста, который увидит агент."""
    id: str  # id элемента, например "raw-e-0003"
    kind: str  # constraint (стоячее правило) | fact | summary | raw (запись как есть) | quoted_data (недоверенное, в кавычках)
    text: str  # текст, который попадёт в промпт
    entry_ids: tuple[str, ...] = ()  # записи, из которых элемент получен (для трассировки)
    disputed: bool = False  # True, если два источника равной силы противоречат друг другу
    superseded: bool = False  # True, если значение уже заменено более новым


@dataclass
class Context:
    """Итог работы памяти: элементы и их суммарный размер в токенах."""
    items: list[ContextItem] = field(default_factory=list)  # элементы в том порядке, в котором их увидит агент
    token_count: int = 0  # сумма токенов элементов; не должна превышать бюджет системы

    def render(self) -> str:
        """Склеивает тексты элементов в один блок для промпта."""
        return "\n".join(item.text for item in self.items)
