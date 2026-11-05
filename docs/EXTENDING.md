# Как добавить свою систему памяти

В проекте нет динамического реестра плагинов. Чтобы включить свою память в существующий раннер, нужно **реализовать [`MemorySystem`](../src/mam/systems/base.py#L21) и явно зарегистрировать имя** в фабрике [`mam.systems.create`](../src/mam/systems/__init__.py). Дальше её можно проверить без модели на `dev`, не меняя сохранённые результаты.

Ниже — минимальная демонстрационная `recent_visible`: она хранит только две последние видимые записи. Это **пример интерфейса**, а не предложенная улучшенная базовая система.

## 1. Реализация

Создайте `src/mam/systems/recent_visible.py`:

```python
from mam.systems.base import MemorySystem, make_context
from mam.tokens import count
from mam.types import Context, ContextItem, Reader


class RecentVisible(MemorySystem):
    def context(self, reader: Reader) -> Context:
        selected: list[ContextItem] = []
        used = 0
        # _visible() сначала фильтрует scope/task_id, затем сортирует по clock.
        for entry in reversed(self._visible(reader)):
            if len(selected) == 2:
                break
            cost = count(entry.text)
            if used + cost > self.limit:
                continue
            selected.append(ContextItem(
                id=f"recent-{entry.id}", kind="raw", text=entry.text,
                entry_ids=(entry.id,),
            ))
            used += cost
        return make_context(list(reversed(selected)))
```

`write` с защитой от повторных `id` и `end_session` по умолчанию уже реализованы в базовом классе. `Context.token_count` считает [`make_context`](../src/mam/systems/base.py). Здесь **нет извлечения LLM**, разрешения конфликтов или защиты от инструкций из источника: это простая сырая память для проверки подключения.

## 2. Зарегистрировать имя

В [`src/mam/systems/__init__.py`](../src/mam/systems/__init__.py):

1. Импортируйте `RecentVisible`.
2. Добавьте `"recent_visible"` в кортеж `NAMES`.
3. В `create(...)`, **после проверки имени и аргументов**, добавьте ветку `if name == "recent_visible": return RecentVisible(limit)` перед ветками существующих систем.

Не меняйте `DEFAULT_SYSTEMS` в [`memory_eval.py`](../src/mam/memory_eval.py): новая система должна запускаться явно. Не меняйте исторические таблицы и исходные названия `ours`.

Для памяти с собственными LLM-вызовами дополнительно потребуется передать `llm` из [`live.run_live`](../src/mam/live.py) и реализовать `drain_llm_calls`; для офлайн-прогона надо заранее выбрать способ детерминированного извлечения. Пример выше этого не требует.

## 3. Проверить контракт до эксперимента

Добавьте `tests/unit/test_recent_visible.py`:

```python
from mam.systems import create
from mam.types import Entry, Reader


def entry(id, clock, author, scope, text):
    return Entry(
        id=id, clock=clock, session=1, author=author,
        kind="agent_note", text=text, scope=scope,
        source="agent", trust="agent", origin=None, task_id="task-1",
    )


def test_recent_visible_scope_idempotency_and_limit():
    memory = create("recent_visible", limit=100)
    memory.write(entry("shared", 1, "planner", "shared", "public fact"))
    memory.write(entry("private", 2, "worker", "private", "SECRET"))
    memory.write(entry("latest", 3, "reviewer", "task", "new fact"))
    memory.write(entry("latest", 4, "reviewer", "task", "should be ignored"))
    reader = Reader(role="planner", task_id="task-1", session=1, query="fact")
    context = memory.context(reader)
    assert "public fact" in context.render()
    assert "new fact" in context.render()
    assert "SECRET" not in context.render()
    assert "should be ignored" not in context.render()
    assert context.token_count <= 100
```

Запуск из корня проекта после `make venv`:

```bash
make test
```

Дополнительно проверьте, что контекст с маленьким `limit` не выходит за предел, что чужая `task` не видна и что `write` не зависит от повторного `id`. Для сложной системы нужны проверки `scopes`, `trust`, обновлений, конфликтов и `end_session` — ориентир: [спецификация](SCENARIO_FORMAT.md#8-интерфейс-системы-памяти) и [существующие тесты](../tests/acceptance/).

## 4. Сравнить без модели и без перезаписи архива

Новый каталог — **вне** `results/memory_level/eval/`:

```bash
PYTHONPATH=src .venv/bin/python -m mam.memory_eval \
  --split dev --systems recent_visible \
  --out /tmp/mam-recent-visible

PYTHONPATH=src .venv/bin/python -m mam.tables \
  /tmp/mam-recent-visible --title "recent_visible, dev" \
  > /tmp/mam-recent-visible/tables.md
```

Получатся `recent_visible.jsonl`, `timing/recent_visible.jsonl` и `tables.md`. Числа по `dev` **нельзя** сравнивать с основными итогами по `eval` как с одним экспериментом. Для честного парного офлайн-сравнения явно запустите те же системы на **одном сплите и одних сценариях**, в отдельном каталоге, затем используйте `mam.tables`.

## 5. Живой эксперимент: отдельно и платно

Если требуется проверить действия агентов, раннер принимает явный `--systems`, но `make live` использует фиксированный список и не подхватит новое имя автоматически. Пример после [`make doctor`](RUNBOOK.md#3-живой-слой-платный-запуск):

```bash
PYTHONPATH=src .venv/bin/python -m mam.run live \
  --split dev --select smoke --systems recent_visible \
  --repeats 1 --workers 1 --max-cost-usd 0.25 \
  --out results/live/recent_visible_smoke
```

Это **платный вызов**; `--max-cost-usd` — мягкий предел, который может быть превышен. Результат сохраняется отдельно; не используйте `results/live/main`. Нельзя подменять этим прогоном значения исходных таблиц без нового протокола, манифеста и [записи о версии эксперимента](EXPERIMENT_VERSIONS.md).

**Перед публикацией результата:** укажите коммит, имя системы, источник фактов, лимит токенов, версию модели, сплит/сценарии, число повторов, определение метрики и путь к исходным файлам. Матрица условий — в [постановке](PROBLEM.md#сравнимость-систем), безопасные способы проверки — в [руководстве по запускам](RUNBOOK.md).
