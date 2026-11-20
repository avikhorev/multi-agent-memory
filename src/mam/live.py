"""Одна живая единица: сценарий, который разыгрывают агенты-модели против одной системы памяти.

В каждой сессии: записываются сообщения пользователя, затем по очереди работают Planner, Worker (два вызова:
выбрать действие, затем отчитаться) и Reviewer, каждый на контексте, собранном только из памяти. Заметки,
которые возвращают агенты, записываются обратно в память. Заготовленные заметки-конфликты и личные черновики
(заметки фактора сценария) пишет сам стенд, потому что агенты сами их не создали бы; обычные заготовленные
заметки в живом прогоне не записываются.
"""
from __future__ import annotations

import dataclasses
import json
import time

from mam.agents import AgentResult, run_agent
from mam.llm import LLMClient
from mam.scoring import label_failure, score_action, score_context
from mam.simulate import Simulator, entries
from mam.systems import create
from mam.types import Context, Entry, Reader

# Задачи по умолчанию, когда в сессии нет контрольной точки с вопросом для этой роли.
GENERIC_PLANNER_TASK = "Decide what the Worker should do next, based on the user's message and the memory."
FALLBACK_WORKER_TASK = "Continue the project work."


def _call_record(role: str, session: int, out) -> dict:
    """Плоская запись об одном вызове модели для отчёта: расход токенов, стоимость, время, отказ."""
    u = out.usage
    return {"role": role, "session": session, "input_tokens": u.input_tokens,
            "cache_creation_tokens": u.cache_creation_tokens, "cache_read_tokens": u.cache_read_tokens,
            "output_tokens": u.output_tokens, "thinking_tokens": u.thinking_tokens, "cost_usd": u.cost_usd,
            "latency_s": round(out.latency_s, 3), "refusal": out.refusal}


def session_source(scenario, session: int):
    """Единственный источник данных, предложенный Worker в сессии: источник фактора, если есть, иначе первый.
    Предлагаем один, чтобы поведение не зависело от выбора между источниками."""
    evs = [e for e in scenario.sessions[session - 1].events if e.type == "tool_data"]
    return next((e for e in evs if e.factor), evs[0] if evs else None)


def reachable(scenario, cp, offered: set[str]) -> bool:
    """Могла ли информация контрольной точки попасть в память по правилам протокола?

    Сообщения пользователя и заметки-конфликты и черновики сценария пишутся всегда; источник инструмента — только
    если он предложен Worker в своей сессии; обычные заготовленные заметки в живом прогоне не пишутся.
    Нужно, чтобы не винить память за информацию, которая до неё физически не дошла.
    """
    events = {e.id: (e, sess.index) for sess in scenario.sessions for e in sess.events}
    for rid in cp.required_events:
        e, _ = events[rid]
        if e.type == "user_message" or (e.type == "note" and e.factor) or (e.type == "tool_data" and rid in offered):
            return True
    return False


def _source_line(ev) -> str:
    """Строка источника для промпта Worker: инструмент, аргументы и краткое «о чём» (первая строка текста)."""
    return f"tool: {ev.tool}, args: {json.dumps(ev.args, sort_keys=True)} (about: {ev.text.split(chr(10))[0][:60]})"


EMPTY_ACTION = {"tool": "none", "args": {}, "answer": "", "notes": []}  # действие, если агент ничего не вернул
READ_TOOLS = ("read_document", "read_status")  # инструменты чтения: их результат становится записью памяти


@dataclasses.dataclass
class Turn:
    """Ход одного агента в сессии: его ответ и контекст памяти, на котором он получен."""
    res: AgentResult
    ctx: Context

    @property
    def action(self) -> dict:
        return self.res.action or EMPTY_ACTION


class LiveUnit:
    """Состояние одной живой единицы: система памяти, симулятор, журналы и шаги сессии.

    Порядок операций (запись, чтение, вызовы модели, трасса) задан протоколом прогона: от него зависит
    содержимое трассы и логических часов, поэтому шаги вызываются строго в порядке `play_session`.
    """

    def __init__(self, scenario, cfg: str, llm: LLMClient, limit: int):
        # Модельный извлекатель нужен только тем системам, что что-то извлекают.
        self.system = (create(cfg, limit=limit, extractor="llm", llm=llm) if cfg in ("ours", "rolling_summary")
                       else create(cfg, limit=limit))
        self.scenario, self.cfg, self.llm = scenario, cfg, llm
        self.sim = Simulator(scenario)  # ответы инструментов из сценария
        self.events = {e.id: e for sess in scenario.sessions for e in sess.events}
        # Событие tool_data по (инструмент, аргументы): по нему находим, какой записью стал вызов агента.
        self.tool_events = {(e.tool, json.dumps(e.args, sort_keys=True)): e
                            for e in self.events.values() if e.type == "tool_data"}
        self.by_session: dict[int, list[Entry]] = {}
        for e in entries(scenario):
            self.by_session.setdefault(e.session, []).append(e)
        self.task_id = f"task-{scenario.id}"
        self.offered = {src.id for k in range(1, scenario.n_sessions + 1) if (src := session_source(scenario, k))}
        self.trace: list[dict] = []  # журнал операций для разбора: запись, чтение, вызовы, действия, проверки
        self.seen_memory_ops: set[str] = set()  # уже выписанные решения памяти (они пересчитываются при каждом чтении)
        self.calls: list[dict] = []  # записи о вызовах модели
        self.checkpoints: list[dict] = []  # результаты контрольных точек
        self.written_events: set[str] = set()  # события сценария, ставшие записями памяти (для метки «agent»)
        self.clock = 0  # общие логические часы: порядок записи определяет стенд, а не сценарий
        self.memory_s = 0.0  # время работы самой памяти
        self.n_notes = 0  # счётчик id заметок агентов

    # --- обмен с памятью и моделью ---

    def drain(self, session: int) -> float:
        """Записать вызовы модели, которые память сделала сама (извлечение, сводки); вернуть их время,
        чтобы вычесть из времени самой памяти."""
        total = 0.0
        for role, out in self.system.drain_llm_calls():
            self.calls.append(_call_record(role, session, out))
            total += out.latency_s
        for rec in self.system.drain_extractions():
            self.trace.append(dict(rec, op="extraction", clock=self.clock))
        return total

    def write(self, entry: Entry, session: int, event_id: str | None = None) -> None:
        """Записать в память с новыми часами и отметить в трассе."""
        self.clock += 1
        entry = dataclasses.replace(entry, clock=self.clock)
        t0 = time.perf_counter()
        self.system.write(entry)
        self.memory_s += time.perf_counter() - t0
        self.trace.append({"op": "write", "clock": entry.clock, "entry_id": entry.id, "scope": entry.scope,
                           "trust": entry.trust, "author": entry.author, "kind": entry.kind, "session": session})
        if event_id:
            self.written_events.add(event_id)

    def read(self, role: str, session: int, query: str) -> Context:
        """Запросить контекст у памяти от имени роли и записать чтение в трассу."""
        reader = Reader(role=role, task_id=self.task_id, session=session, query=query)
        t0 = time.perf_counter()
        ctx = self.system.context(reader)
        self.memory_s += time.perf_counter() - t0
        self.trace.append({"op": "read", "clock": self.clock, "reader": role,
                           "item_ids": [i.id for i in ctx.items], "token_count": ctx.token_count})
        for t in getattr(self.system, "last_trace", []):  # решения пересчитываются при каждом чтении: выписываем каждое один раз
            ident = json.dumps(t, sort_keys=True)
            if ident not in self.seen_memory_ops:
                self.seen_memory_ops.add(ident)
                self.trace.append(dict(t, clock=self.clock))
        return ctx

    def ask(self, role: str, session: int, ctx: Context, task: str, **kw) -> AgentResult:
        """Вызвать агента на готовом контексте и записать вызовы и действие в трассу."""
        res = run_agent(self.llm, role, context=ctx.render(), task=task, session=session, **kw)
        self.calls.extend(_call_record(role, session, c) for c in res.calls)
        for c in res.calls:
            self.trace.append({"op": "llm_call", "clock": self.clock, "role": role, "session": session,
                               "refusal": c.refusal, "latency_s": round(c.latency_s, 3), "cost_usd": c.usage.cost_usd})
        act = res.action or {}
        self.trace.append({"op": "agent_action", "clock": self.clock, "role": role, "session": session,
                           "tool": act.get("tool"), "args": act.get("args"), "answer": (act.get("answer") or "")[:200],
                           "error": res.error, "refusal": res.refusal})
        return res

    def save_notes(self, role: str, session: int, res: AgentResult, tool_entry_id: str | None = None) -> None:
        """Записать заметки агента обратно в память. Заметка Worker после чтения инструмента пересказывает
        недоверенные данные, поэтому наследует недоверие и источник (иначе заметка «отмыла» бы вредный текст)."""
        for text in (res.action or {}).get("notes", []):
            self.n_notes += 1
            derived = role == "worker" and tool_entry_id is not None
            self.write(Entry(id=f"n-{session}-{role}-{self.n_notes}", clock=0, session=session, author=role,
                             kind="agent_note", text=text, scope="task", source="tool" if derived else "agent",
                             trust="untrusted" if derived else "agent", origin=tool_entry_id, task_id=self.task_id),
                       session)

    # --- шаги сессии ---

    def write_harness_entries(self, k: int) -> str:
        """Стенд пишет то, что агенты сами не создали бы: сообщения пользователя, заметки-конфликты и черновики
        фактора. Возвращает объединённый текст сообщений пользователя."""
        sess_entries = self.by_session.get(k, [])
        for e in sess_entries:
            ev = self.events[e.id]
            if e.kind == "user_message" or (e.kind in ("agent_note", "draft") and ev.factor):
                self.write(e, k, e.id)
        return " ".join(e.text for e in sess_entries if e.kind == "user_message")

    def planner_turn(self, k: int, user_text: str, cps: dict) -> Turn:
        """Planner видит сообщение пользователя; свой вопрос берёт из контрольной точки, если она есть."""
        task = cps["planner"].task_text if "planner" in cps else GENERIC_PLANNER_TASK
        ctx = self.read("planner", k, user_text + " " + task)
        res = self.ask("planner", k, ctx, task, user_message=user_text)
        self.save_notes("planner", k, res)
        return Turn(res, ctx)

    def worker_turn(self, k: int, planner: Turn, cps: dict) -> tuple[Turn, AgentResult, list[dict]]:
        """Worker: первый вызов выбирает действие, затем стенд выполняет его, второй вызов отчитывается по результату.
        Возвращает ход (второй вызов), первый вызов (нужен для учёта отказа) и выполненные действия."""
        task = (cps["worker"].task_text if "worker" in cps
                else planner.action["answer"] or FALLBACK_WORKER_TASK)
        ctx = self.read("worker", k, task)
        src = session_source(self.scenario, k)
        sources = [_source_line(src)] if src else []
        w1 = self.ask("worker", k, ctx, task, sources=sources)
        a1 = w1.action or EMPTY_ACTION
        actions, tool_entry_id, tool_result = [], None, "(no tool was used)"
        if a1["tool"] in READ_TOOLS:
            tool_result = self.sim.call(a1["tool"], a1["args"])
            tool_entry_id = self.record_tool_read(k, a1, tool_result)
        elif a1["tool"] == "update_record":
            tool_result = self.sim.call("update_record", a1["args"])
        if a1["tool"] != "none":
            actions.append({"tool": a1["tool"], "args": a1["args"]})
        w2 = self.ask("worker", k, ctx, task, sources=sources, tool_result=tool_result)
        a2 = w2.action or EMPTY_ACTION
        if a2["tool"] == "update_record":
            self.sim.call("update_record", a2["args"])
            actions.append({"tool": "update_record", "args": a2["args"]})
        self.save_notes("worker", k, w2, tool_entry_id)
        return Turn(w2, ctx), w1, actions

    def record_tool_read(self, k: int, call: dict, result: str) -> str | None:
        """Прочитанные данные становятся записью памяти (недоверенной): так они попадают в память только если
        агент их прочитал. Возвращает id записи или None, если такого события в сценарии нет."""
        ev = self.tool_events.get((call["tool"], json.dumps(call["args"], sort_keys=True)))
        if ev is None:
            return None
        kind = "document" if call["tool"] == "read_document" else "tool_output"
        self.write(Entry(id=ev.id, clock=0, session=k, author="worker", kind=kind, text=result, scope="task",
                         source="document" if kind == "document" else "tool", trust="untrusted", origin=None,
                         task_id=self.task_id), k, ev.id)
        return ev.id

    def reviewer_turn(self, k: int, worker: Turn, cps: dict) -> Turn:
        """Reviewer проверяет результат Worker."""
        task = cps["reviewer"].task_text if "reviewer" in cps else f"Review this result: {worker.action['answer']}"
        ctx = self.read("reviewer", k, task)
        res = self.ask("reviewer", k, ctx, task)
        self.save_notes("reviewer", k, res)
        return Turn(res, ctx)

    def score_checkpoints(self, k: int, cps: dict, turns: dict[str, Turn], worker_refused: bool,
                          actions: list[dict]) -> None:
        """Оцениваем и ответ (уровень действия), и контекст (уровень памяти) — по их расхождению ставится метка,
        кто виноват. worker_refused: отказ на первом вызове Worker считается отказом роли."""
        for role, cp in cps.items():
            turn = turns[role]
            refused = turn.res.refusal or (role == "worker" and worker_refused)
            action = turn.action
            role_actions = actions if role == "worker" else []
            output = {"answer": action["answer"], "actions": role_actions}
            label = label_failure(self.scenario, cp.id, refusal=refused, written_event_ids=self.written_events,
                                  context=turn.ctx, agent_output=None if refused else output)
            verdict = score_action(self.scenario, cp.id, output)
            passed = (not refused) and verdict.passed
            self.checkpoints.append({
                "checkpoint": cp.id, "role": role, "kind": cp.kind, "factor": cp.factor, "session": k,
                "passed": passed, "label": label,
                "context_passed": score_context(self.scenario, cp.id, turn.ctx).passed,
                "reachable": reachable(self.scenario, cp, self.offered),
                "answer": action["answer"], "actions": role_actions, "token_count": turn.ctx.token_count,
                "refusal": refused, "violations": [] if passed else verdict.violations})
            self.trace.append({"op": "check", "clock": self.clock, "checkpoint_id": cp.id, "passed": passed})
            self.trace.append({"op": "label", "clock": self.clock, "checkpoint_id": cp.id, "label": label})

    def end_session(self, k: int) -> None:
        """Конец сессии: память извлекает факты/строит сводку; её собственные вызовы модели из времени памяти вычитаем."""
        t0 = time.perf_counter()
        self.system.end_session(k)
        elapsed = time.perf_counter() - t0
        self.memory_s += max(0.0, elapsed - self.drain(k))

    def play_session(self, k: int) -> None:
        user_text = self.write_harness_entries(k)
        cps = {cp.role: cp for cp in self.scenario.checkpoints if cp.session == k}
        planner = self.planner_turn(k, user_text, cps)
        worker, w1, actions = self.worker_turn(k, planner, cps)
        reviewer = self.reviewer_turn(k, worker, cps)
        self.score_checkpoints(k, cps, {"planner": planner, "worker": worker, "reviewer": reviewer},
                               w1.refusal, actions)
        self.end_session(k)

    # --- итог ---

    def totals(self) -> dict:
        """Итоги по единице: вызовы, отказы, стоимость, время и токены (входные — все виды)."""
        calls = self.calls
        return {"llm_calls": len(calls), "refusals": sum(c["refusal"] for c in calls),
                "cost_usd": round(sum(c["cost_usd"] for c in calls), 6),
                "llm_latency_s": round(sum(c["latency_s"] for c in calls), 3),
                "memory_s": round(self.memory_s, 4),
                "input_tokens": sum(c["input_tokens"] + c["cache_creation_tokens"] + c["cache_read_tokens"]
                                    for c in calls),
                "output_tokens": sum(c["output_tokens"] for c in calls)}

    def memory_stats(self) -> dict:
        """Сведения о работе памяти: сколько задержал карантин, сколько отказов и ошибок разбора при извлечении."""
        extractor = getattr(self.system, "_extractor", None)
        return {"quarantined": len(getattr(self.system, "quarantined", [])),
                "extraction_refusals": len(getattr(self.system, "refusals", [])),
                "parse_errors": getattr(extractor, "parse_errors", 0)}

    def result(self, repeat: int) -> dict:
        return {"scenario": self.scenario.id, "system": self.cfg, "repeat": repeat, "checkpoints": self.checkpoints,
                "calls": self.calls, "memory": self.memory_stats(), "totals": self.totals(), "trace": self.trace,
                "actions": list(self.sim.action_log)}


def run_live(scenario, cfg: str, llm: LLMClient, *, repeat: int = 0, limit: int = 2000) -> dict:
    """Разыгрывает сценарий с системой памяти cfg; возвращает словарь результата единицы
    (контрольные точки, вызовы, итоги, трасса, действия)."""
    unit = LiveUnit(scenario, cfg, llm, limit)
    for k in range(1, scenario.n_sessions + 1):
        unit.play_session(k)
    return unit.result(repeat)
