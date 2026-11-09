"""Структурированная память: факты с датами, области видимости, правила конфликтов, карантин и закреплённые ограничения.

Факты извлекаются один раз за сессию. При чтении версии, видимые читателю, разрешаются
по ключу (сущность, атрибут) в порядке записи. Старые версии не удаляются, а решение
принимается только при чтении: так области видимости, срок действия и доверие можно
по отдельности отключать для абляций (измерения вклада каждого механизма).
"""
from __future__ import annotations

from dataclasses import dataclass

from mam.extractors import UNKNOWN_TIME, make_extractor, rule_constraints
from mam.guard import split_untrusted
from mam.systems.base import MemorySystem, make_context, visible_to
from mam.systems.ranking import bm25_scores
from mam.tokens import count
from mam.types import Context, ContextItem, Entry, Fact, Reader

# Авторитет источника факта: при равном времени выигрывает больший. Пользователь главнее инструмента,
# инструмент главнее документа, документ главнее заметки агента.
AUTHORITY = {"user": 3, "tool": 2, "document": 1, "agent": 0}
# Доверие к записи как к носителю команд: недоверенное (0) не может перебить доверенное.
TRUST = {"trusted": 2, "agent": 1, "untrusted": 0}


def _norm(text: str) -> str:
    """Вид текста для сравнения подстрок: без регистра, пробелов и запятых (разделителей тысяч)."""
    return "".join(text.lower().replace(",", "").split())


@dataclass
class Version:
    """Одна версия факта вместе с тем, откуда она взялась. Нужна для разрешения конфликтов."""
    fact: Fact  # сам факт
    entry: Entry  # запись, из которой факт извлечён (область видимости, доверие, порядок записи)
    time: int  # момент события (день); UNKNOWN_TIME (-1), если в тексте он не назван
    authority: int  # авторитет источника по таблице AUTHORITY
    trust: int  # доверие к записи по таблице TRUST


class Ours(MemorySystem):
    """Наша система памяти. Записи накапливаются, в конце сессии из них извлекаются факты,
    а при чтении контекст собирается из ограничений, разрешённых фактов и безопасных фрагментов."""

    def __init__(self, limit: int, ablate=frozenset(), extractor: str = "oracle", cache_path=None, llm=None):
        super().__init__(limit)
        self.ablate = frozenset(ablate)  # какие механизмы отключены (validity | scopes | trust | pinned_constraints)
        self._extractor = make_extractor(extractor, cache_path, llm)
        self._done: set[str] = set()  # id записей, уже обработанных извлекателем (повторно не извлекаем)
        # Все версии каждого факта по ключу (сущность, атрибут); отклонённые тоже хранятся, решение — при чтении.
        self._versions: dict[tuple[str, str], list[Version]] = {}
        self._constraints: list[tuple[Entry, str]] = []  # закреплённые ограничения: (запись, текст); не версионируются
        self._fragments: list[tuple[Entry, str]] = []  # безопасные куски недоверенных текстов, не ставшие фактами
        self.quarantined: list[tuple[str, str]] = []  # (id записи, фрагмент), задержанные карантином
        self.refusals: list[str] = []  # id записей, извлечение которых модель отказалась делать
        self.last_trace: list[dict] = []  # трасса последнего context(): quarantine / resolve / reject, для объяснимости

    # ---- запись ----

    def end_session(self, session: int) -> None:
        """Извлекаем факты из записей завершённой сессии (по порядку часов)."""
        for e in sorted(self._entries.values(), key=lambda e: e.clock):
            if e.session == session and e.id not in self._done:
                self._done.add(e.id)
                self._ingest(e)

    def _ingest(self, e: Entry) -> None:
        """Обрабатывает одну запись: извлекает факты и ограничения, пропускает недоверенный текст через карантин."""
        # Модельному извлекателю подсказываем уже известные факты, чтобы он понял относительные обновления
        # («сократили на 25 процентов»); остальным подсказки не нужны.
        ex = (self._extractor.extract(e, known=self.known_lines(e.text))
              if getattr(self._extractor, "wants_known", False) else self._extractor.extract(e))
        if ex.refused:
            self.refusals.append(e.id)
        trust_on = "trust" not in self.ablate
        if "pinned_constraints" not in self.ablate:
            # Без фильтра доверия ограничения берутся и из недоверенных записей: так измеряется вред от отсутствия фильтра.
            texts = ex.constraints if trust_on else (ex.constraints or rule_constraints(e, require_trusted=False))
            self._constraints.extend((e, t) for t in texts)
        # Недоверенный текст — данные, а не команды: пропускаем через карантин.
        if e.trust == "untrusted" and e.kind in ("tool_output", "document"):
            if trust_on:
                kept, held = split_untrusted(e.text)
                values = [_norm(f.value) for f in ex.facts]
                # фрагмент, из которого уже извлечён факт, представлен этим фактом, а не сырым текстом (без дублей)
                self._fragments.extend((e, f) for f in kept if not any(v in _norm(f) for v in values))
                self.quarantined.extend((e.id, f) for f in held)
            else:
                self._fragments.append((e, e.text))  # без фильтра: текст идёт как есть
        # Каждый факт — новая версия под своим ключом; старые не стираем.
        for f in ex.facts:
            self._versions.setdefault((f.entity, f.attribute), []).append(
                Version(f, e, f.valid_from, AUTHORITY.get(f.source, 0), TRUST[e.trust]))

    def known_lines(self, text: str, k: int = 8) -> list[str]:
        """Текущие общие факты, наиболее близкие к `text` (до k штук), — подсказка модели для чтения относительных обновлений.
        Личные (private) версии не берём: подсказка не должна раскрывать чужое."""
        lines = []
        for key in sorted(self._versions):
            vis = [v for v in self._versions[key] if v.entry.scope != "private"]
            for v in self._resolve(vis) if vis else []:
                lines.append(f"{v.fact.entity} {v.fact.attribute} = {v.fact.value}")
        scores = bm25_scores(text, lines)
        return [l for _, l in sorted(zip(scores, lines), key=lambda p: (-p[0], p[1]))[:k]]

    def drain_llm_calls(self) -> list:
        """Вызовы модели извлекателем (если он их делает) — для учёта стоимости."""
        return self._extractor.drain() if hasattr(self._extractor, "drain") else []

    def drain_extractions(self) -> list[dict]:
        """Журнал извлечений (для сохранения в кеш)."""
        return self._extractor.drain_log() if hasattr(self._extractor, "drain_log") else []

    # ---- чтение ----

    def _can_see(self, e: Entry, reader: Reader) -> bool:
        """Видна ли запись читателю; при абляции scopes видно всё."""
        return True if "scopes" in self.ablate else visible_to(e, reader)

    def _resolve(self, versions: list[Version]) -> list[Version]:
        """Действующие версии одного ключа из видимых версий, в порядке записи.

        Правила, когда приходит новая версия v при уже действующей c:
        - то же значение: оставляем более доверенную (подтверждение);
        - абляция validity или нет действующей: просто добавляем (версий может быть несколько);
        - недоверенная против доверенной: отклоняем (недоверенный текст не переписывает факты);
        - иначе: позднее событие побеждает; при равном времени — больший авторитет;
          при равном авторитете — спор (храним обе версии, помечаем DISPUTED).
        Результат — список; больше одного элемента означает спор.
        """
        validity, trust_on = "validity" not in self.ablate, "trust" not in self.ablate
        current: list[Version] = []
        latest = 0
        for v in sorted(versions, key=lambda v: v.entry.clock):
            v = Version(v.fact, v.entry, v.time, v.authority, v.trust)  # копия: исходную версию не меняем
            if v.time == UNKNOWN_TIME:
                v.time = latest + 1  # время не названо: считаем событие более поздним, чем всё виденное
            key = f"{v.fact.entity}/{v.fact.attribute}"  # для трассы
            same = next((c for c in current if c.fact.value == v.fact.value), None)
            if same is not None:
                if v.trust > same.trust:  # a more trusted source confirms the value
                    current[current.index(same)] = v
            elif not validity or not current:
                current.append(v)
            elif trust_on and v.trust == 0 and current[0].trust > 0:
                self.last_trace.append({"op": "reject", "key": key, "entry_id": v.entry.id,
                                        "reason": "untrusted source cannot override a trusted fact"})
            else:
                c = current[0]
                if v.time > c.time:
                    self._note_resolve(key, v, c, "later_event")
                    current = [v]
                elif v.time < c.time:
                    self.last_trace.append({"op": "reject", "key": key, "entry_id": v.entry.id, "reason": "older event"})
                elif v.authority > c.authority:
                    self._note_resolve(key, v, c, "authority")
                    current = [v]
                elif v.authority < c.authority:
                    self.last_trace.append({"op": "reject", "key": key, "entry_id": v.entry.id, "reason": "lower authority"})
                else:
                    self.last_trace.append({"op": "resolve", "key": key, "winner": None, "loser": None, "rule": "disputed"})
                    current.append(v)
            latest = max(latest, v.time)
        return current

    def _note_resolve(self, key: str, winner: Version, loser: Version, rule: str) -> None:
        """Запись в трассу о том, какая версия победила и по какому правилу."""
        self.last_trace.append({"op": "resolve", "key": key, "winner": winner.fact.value, "loser": loser.fact.value,
                                "rule": rule})

    def _fact_items(self, reader: Reader) -> list[tuple[ContextItem, int]]:
        """Разрешённые факты как элементы контекста; вместе с каждым — его время (для сортировки при равной релевантности)."""
        trust_on = "trust" not in self.ablate
        items: list[tuple[ContextItem, int]] = []
        for key in sorted(self._versions):
            visible = [v for v in self._versions[key] if self._can_see(v.entry, reader)]
            if not visible:
                continue
            cur = self._resolve(visible)
            # Спор (несколько версий) показываем одним элементом; при абляции validity каждая версия идёт отдельно.
            groups = [cur] if len(cur) > 1 and "validity" not in self.ablate else [[v] for v in cur]
            for g in groups:
                f = g[0].fact
                disputed = len(g) > 1
                # Факт из недоверенного источника подаём как цитируемые данные, помеченные [data].
                quoted = trust_on and any(v.entry.trust == "untrusted" for v in g)
                if disputed:
                    body = " | ".join(f"{v.fact.value} (per {v.fact.source})" for v in g)
                    text = f"{f.entity} {f.attribute}: {body} [DISPUTED]"
                else:
                    text = f"{f.entity} {f.attribute}: {f.value}"
                if quoted:
                    text = "[data] " + text
                item = ContextItem(id=f"fact-{f.entity}-{f.attribute}-{g[0].entry.id}", kind="quoted_data" if quoted else "fact",
                                   text=text, entry_ids=tuple(v.entry.id for v in g), disputed=disputed)
                items.append((item, max(v.time for v in g)))
        return items

    def context(self, reader: Reader) -> Context:
        """Собирает контекст в порядке важности: ограничения (всегда), затем факты и фрагменты по релевантности в оставшийся бюджет."""
        self.last_trace = []
        out: list[ContextItem] = []
        seen: set[str] = set()
        # Ограничения идут первыми и не обрезаются: пропустить правило пользователя опаснее, чем пропустить факт.
        for e, text in self._constraints:
            if self._can_see(e, reader) and text not in seen:
                seen.add(text)
                out.append(ContextItem(id=f"constraint-{e.id}-{len(out)}", kind="constraint", text=text, entry_ids=(e.id,)))
        used = sum(count(i.text) for i in out)
        if used > self.limit:  # ограничения не помещаются — это ошибка конфигурации, молча обрезать нельзя
            raise ValueError(f"pinned constraints need {used} tokens, the limit is {self.limit}")
        # Отмечаем в трассе все задержанные фрагменты (по ним видно, что карантин сработал).
        for e_id, frag in self.quarantined:
            self.last_trace.append({"op": "quarantine", "entry_id": e_id, "reason": "instruction-like fragment"})

        facts = self._fact_items(reader)
        frags = [(ContextItem(id=f"frag-{e.id}-{n}", kind="raw" if "trust" in self.ablate else "quoted_data", text=t,
                              entry_ids=(e.id,)), e.clock)
                 for n, (e, t) in enumerate(self._fragments) if self._can_see(e, reader)]
        # Факты важнее сырых фрагментов, поэтому берём их первыми; каждая группа ранжируется по BM25,
        # а при равной оценке побеждает более свежая; элемент, не влезший в бюджет, пропускается.
        for group in (facts, frags):
            scores = bm25_scores(reader.query, [i.text for i, _ in group])
            ranked = sorted(zip(scores, group), key=lambda p: (-p[0], -p[1][1], p[1][0].id))
            for _, (item, _) in ranked:
                cost = count(item.text)
                if used + cost <= self.limit:
                    out.append(item)
                    used += cost
        return make_context(out)
