"""Симулятор инструментов и лента записей памяти (раздел 4 спецификации)."""
from __future__ import annotations

import json

from .scenario import Scenario
from .types import Entry

def _key(tool: str, args: dict) -> tuple[str, str]:
    """Ключ поиска ответа: имя инструмента и аргументы в каноническом виде
    (sort_keys, чтобы порядок аргументов не влиял на совпадение)."""
    return (tool, json.dumps(args, sort_keys=True))

class Simulator:
    """Возвращает tool_data сценария по паре (инструмент, аргументы); update_record только пишет в журнал действий.

    Нужен, чтобы агент мог «вызывать инструменты» без реальных систем: все ответы
    заранее записаны в сценарии, поэтому прогон воспроизводим.
    """

    def __init__(self, scenario: Scenario):
        # Таблица готовых ответов: берём все события tool_data из всех сессий.
        self._data = {_key(e.tool, e.args): e.text
                      for sess in scenario.sessions for e in sess.events if e.type == "tool_data"}
        # Журнал изменяющих вызовов; по нему потом проверяется, что агент сделал.
        self.action_log: list[dict] = []

    def call(self, tool: str, args: dict) -> str:
        if tool == "update_record":
            # Запись ничего не меняет в данных, но фиксируется для оценки действий агента.
            self.action_log.append({"tool": tool, "args": dict(args)})
            return "OK: change recorded"
        text = self._data.get(_key(tool, args))
        if text is None:
            # Агент позвал то, чего в сценарии нет: возвращаем ошибку, а не выдумываем данные.
            return f"ERROR: no data for {tool} {json.dumps(args, sort_keys=True)}"
        return text

def entries(scenario: Scenario) -> list[Entry]:
    """Одна запись Entry на каждое событие в порядке ленты; часы растут на 1 за запись.

    Здесь же решается, чему доверять (trust) и откуда запись (source):
    это определяет, как система памяти обработает запись дальше.
    """
    facts = {f.id: f for f in scenario.facts}
    task_id = f"task-{scenario.id}"
    out: list[Entry] = []
    clock = 0
    for sess in scenario.sessions:
        # Какое событие tool_data породило данный факт (по id факта) — нужно, чтобы
        # узнать происхождение заметки агента, пересказывающей вывод инструмента.
        tool_events = {fid: e for e in sess.events if e.type == "tool_data" for fid in e.facts}
        for e in sess.events:
            clock += 1
            origin = None
            if e.type == "user_message":
                # Сообщение пользователя — самый доверенный источник.
                kind, source, trust = "user_message", "user", "trusted"
            elif e.type == "tool_data":
                # Данные инструментов и документов — недоверенные: в них может быть внедрена инструкция.
                kind, source, trust = (("document", "document", "untrusted") if e.tool == "read_document"
                                       else ("tool_output", "tool", "untrusted"))
            else:
                # Остальное — записи самого агента: личный черновик или общая заметка.
                kind = "draft" if e.scope == "private" else "agent_note"
                source, trust = "agent", "agent"
                srcs = [tool_events.get(fid) for fid in e.facts]
                if e.facts and all(srcs) and len({x.id for x in srcs}) == 1:
                    # Заметка целиком пересказывает один источник: наследуем его происхождение
                    # и недоверие, чтобы заметка не «отмыла» недоверенные данные.
                    origin = srcs[0].id
                    source = "document" if srcs[0].tool == "read_document" else "tool"
                    trust = "untrusted"
            out.append(Entry(
                id=e.id, clock=clock, session=sess.index, author=e.author, kind=kind, text=e.text,
                scope=e.scope, source=source, trust=trust, origin=origin, task_id=task_id,
                oracle_facts=tuple(facts[fid] for fid in e.facts)))
    return out
