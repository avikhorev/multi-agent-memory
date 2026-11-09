"""Типы сценария и (де)сериализация в JSON (разделы 3 и 7 спецификации).

Сценарий — это воспроизводимая история работы нескольких агентов (сессии и события),
ключ правильных ответов (факты) и контрольные точки, в которых проверяют память.
"""
from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from pathlib import Path

from .types import Fact


@dataclass
class ActionPattern:
    """Шаблон действия агента: совпадает, если инструмент тот же, а в аргументах есть заданные значения."""
    tool: str  # имя инструмента: read_document | read_status | update_record
    args: dict  # значения, которые должны быть в аргументах вызова, например {"field": "atlas.budget_usd"}


@dataclass
class Event:
    """Одно событие истории: реплика пользователя, ответ инструмента или заметка агента."""
    id: str  # уникален: "e-NNNN" для базовых событий, "x-NNNN" для событий фактора
    type: str  # user_message | tool_data | note
    text: str  # что говорит событие; для tool_data — текст, который вернул инструмент
    author: str  # user | planner | worker | reviewer | tool
    scope: str  # task | shared | private; private — черновик, который видит только его автор
    tool: str | None  # только для tool_data: read_document | read_status; иначе None
    args: dict | None  # только для tool_data: аргументы этого вызова, например {"doc_id": "D-12"}
    facts: list[str]  # id фактов эталона (oracle), о которых сообщает событие; ключ для экстрактора и оценки
    factor: bool  # True, если событие добавил фактор категории


@dataclass
class Session:
    """Группа событий одной рабочей сессии; между сессиями у агентов нет своей памяти."""
    index: int  # номер сессии, с 1
    events: list[Event]  # в том порядке, в котором память их получает


@dataclass
class Constraint:
    """Стоячее ограничение пользователя («никогда не делай X»); проверяется в категории C2."""
    id: str  # например "k-0001"
    text: str  # формулировка ограничения пользователя
    introduced_in: int  # номер сессии, в которой пользователь его называет
    event_id: str  # id события user_message, в котором оно названо
    forbidden: list[ActionPattern]  # действия, которые нарушили бы ограничение


@dataclass
class CheckpointContext:
    """Требования к контексту памяти (уровень контекста): что в нём должно и не должно быть."""
    present: list[str] = field(default_factory=list)  # должны быть в собранном контексте
    absent: list[str] = field(default_factory=list)  # не должны появиться в контексте нигде
    absent_outside_quoted: list[str] = field(default_factory=list)  # допустимы только внутри элементов quoted_data
    disputed_both: list[list[str]] = field(default_factory=list)  # пары значений: обе должны быть в контексте и помечены спорными


@dataclass
class CheckpointAnswer:
    """Требования к ответу агента (уровень действия)."""
    expect: str | None = None  # ожидаемый ответ (только для оценки); None, если значение не ожидается
    stale: list[str] = field(default_factory=list)  # замещённые значения, которых не должно быть в ответе
    disputed: bool = False  # True, если ответ должен содержать DISPUTED


@dataclass
class CheckpointAction:
    """Требования к действиям агента с инструментами."""
    forbidden: list[ActionPattern] = field(default_factory=list)  # действия, которых не должно быть (только для оценки)
    required: list[ActionPattern] = field(default_factory=list)  # действия, которые должны быть (только для оценки)


@dataclass
class Checkpoint:
    """Контрольная точка: вопрос агенту в заданный момент и ключ для его автоматической проверки."""
    id: str  # "cp-N" для базовых контрольных точек, "cpx-N" для контрольных точек фактора
    session: int  # номер сессии, в которой задан вопрос
    role: str  # planner | worker | reviewer: чей контекст памяти проверяется
    task_text: str  # вопрос, который получает агент; поля ниже ему не показываются
    kind: str  # что проверяется: value | constraint | conflict | isolation | injection
    context: CheckpointContext  # что контекст памяти должен или не должен содержать
    answer: CheckpointAnswer  # ожидаемый ответ (только для оценки)
    action: CheckpointAction  # ожидаемые и запрещённые действия (только для оценки)
    required_events: list[str]  # id событий, в которых есть ответ; достаточно любого одного
    factor: bool  # True, если контрольную точку добавил фактор категории


@dataclass
class Scenario:
    """Один сценарий бенчмарка. Полный формат: docs/SCENARIO_FORMAT.md, раздел 3."""
    id: str  # уникален: "<category>-<split>-<number>", например "C3-eval-0000"
    category: str  # C0 контроль, C1 обновление, C2 ограничение, C3 конфликт, C4 изоляция, C5 инъекция, C6 длинная история
    split: str  # dev (настройка), eval (основные результаты), holdout (трудные случаи)
    seed: int  # seed генератора; вместе с category, variant и n_sessions однозначно задаёт файл побайтно
    variant: str  # C1 и C3: explicit | implicit; иначе none
    resolution: str  # только C3: later_event | authority | disputed; иначе none
    n_sessions: int  # 10 в C0–C5; 10, 20 или 30 в C6
    sessions: list[Session]  # история, которая передаётся памяти в этом порядке
    facts: list[Fact]  # ключ ответов: все истинные факты мира, включая замещённые
    constraints: list[Constraint]  # ограничения пользователя (C2)
    checkpoints: list[Checkpoint]  # вопросы с их ключами ответов


def to_dict(scenario: Scenario) -> dict:
    """Сценарий в обычный dict (вложенные dataclass разворачиваются рекурсивно)."""
    return dataclasses.asdict(scenario)


def _patterns(items: list[dict]) -> list[ActionPattern]:
    """Список dict из JSON -> список ActionPattern."""
    return [ActionPattern(**p) for p in items]


def from_dict(d: dict) -> Scenario:
    """Обратное к to_dict: вложенные структуры собираем вручную, потому что Event(**e) и т. п. сами их не создают."""
    sessions = [Session(index=s["index"], events=[Event(**e) for e in s["events"]]) for s in d["sessions"]]
    constraints = [
        Constraint(id=c["id"], text=c["text"], introduced_in=c["introduced_in"], event_id=c["event_id"],
                   forbidden=_patterns(c["forbidden"]))
        for c in d["constraints"]
    ]
    checkpoints = []
    for c in d["checkpoints"]:
        checkpoints.append(Checkpoint(
            id=c["id"], session=c["session"], role=c["role"], task_text=c["task_text"], kind=c["kind"],
            context=CheckpointContext(**c["context"]),
            answer=CheckpointAnswer(**c["answer"]),
            action=CheckpointAction(forbidden=_patterns(c["action"]["forbidden"]),
                                    required=_patterns(c["action"]["required"])),
            required_events=c["required_events"], factor=c["factor"]))
    return Scenario(
        id=d["id"], category=d["category"], split=d["split"], seed=d["seed"], variant=d["variant"],
        resolution=d["resolution"], n_sessions=d["n_sessions"], sessions=sessions,
        facts=[Fact(**f) for f in d["facts"]], constraints=constraints, checkpoints=checkpoints)


def dumps(scenario: Scenario) -> str:
    """JSON-текст сценария. sort_keys и фиксированный отступ дают одинаковый результат при каждом запуске
    (нужна побайтовая воспроизводимость); ensure_ascii=False оставляет кириллицу читаемой."""
    return json.dumps(to_dict(scenario), sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def loads(text: str) -> Scenario:
    return from_dict(json.loads(text))


def dump(scenario: Scenario, path) -> None:
    """Пишем байтами, чтобы переводы строк не зависели от ОС."""
    Path(path).write_bytes(dumps(scenario).encode("utf-8"))


def load(path) -> Scenario:
    return loads(Path(path).read_text(encoding="utf-8"))
