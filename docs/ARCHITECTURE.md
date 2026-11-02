# Архитектура

Четыре схемы показывают реализацию: живой слой (`src/mam/live.py`, `src/mam/agents.py`) и память `ours` (`src/mam/systems/ours.py`). Причины решений и числа записаны в [`DECISIONS.md`](DECISIONS.md), модель угроз в [`THREAT_MODEL.md`](THREAT_MODEL.md).

Узлы со значком ↗ открывают соответствующее место в коде на GitHub. Ссылки закреплены на коммите `1811222`: номера строк относятся к нему. На стрелки ссылку поставить нельзя, поэтому в схеме 2 ссылки вынесены в таблицу.

## 1. Система целиком

Агенты не хранят состояние между вызовами: всё, что переходит из сессии в сессию, проходит через память. Системы памяти взаимозаменяемы, потому что у них общий интерфейс `MemorySystem`. На уровне памяти (`src/mam/memory_eval.py`) те же системы проверяются без агентов.

```mermaid
flowchart TB
    scenario["Сценарий ↗<br/>сессии и проверки"] --> loop

    subgraph harness["Живой прогон: run_live"]
        loop["Цикл сессий ↗"]
        sim["Simulator ↗<br/>инструменты Worker"]
        scorer["Оценщик ↗<br/>проверки и метки провалов"]
    end

    subgraph memory["Память"]
        api["MemorySystem ↗<br/>write, context, end_session"]
    end

    subgraph agents["Агенты без состояния"]
        planner["Planner ↗"]
        worker["Worker ↗"]
        reviewer["Reviewer ↗"]
    end

    llm["LLMClient ↗<br/>ClaudeCliClient<br/>claude-haiku-5-5"]
    results["Единицы results/live/ ↗<br/>таблицы и REPORT.md"]

    loop <-->|"записи и контекст до 2000 токенов"| api
    loop <-->|"контекст и задача, ответ и действие"| agents
    loop <--> sim
    loop --> scorer
    scorer --> results
    agents --> llm
    api -.->|"извлечение фактов, только ours"| llm

    click scenario href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/docs/SCENARIO_FORMAT.md"
    click loop href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L130-L203"
    click sim href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/simulate.py#L14"
    click scorer href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/scoring.py#L95"
    click api href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/base.py#L21"
    click planner href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/agents.py#L22"
    click worker href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/agents.py#L25"
    click reviewer href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/agents.py#L31"
    click llm href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/llm.py#L69"
    click results href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/results/live/main/tables.md"
```

## 2. Одна сессия

Worker вызывается дважды: сначала выбирает одно действие, затем сообщает результат. Оба вызова получают один и тот же контекст, поэтому прочитанный документ доходит до второго вызова как результат инструмента, а не из памяти. Факты `ours` извлекаются только в конце сессии; до этого момента новые записи для `ours` не видны.

```mermaid
sequenceDiagram
    autonumber
    participant H as Цикл run_live
    participant M as Память
    participant P as Planner
    participant W as Worker
    participant S as Simulator
    participant R as Reviewer
    participant E as Оценщик

    H->>M: write, сообщения пользователя, конфликтные заметки и черновики сценария

    H->>M: context для Planner
    M-->>H: контекст
    H->>P: контекст, сообщение, задача
    P-->>H: задача для Worker, заметки
    H->>M: write, заметки Planner

    H->>M: context для Worker
    M-->>H: контекст
    H->>W: контекст, задача, источник этой сессии
    W-->>H: одно действие
    alt read_document или read_status
        H->>S: вызов инструмента
        S-->>H: текст источника
        H->>M: write, источник с доверием untrusted
    else update_record
        H->>S: вызов инструмента
        S-->>H: результат
    else none
        Note over H: инструмент не вызван
    end
    H->>W: тот же контекст и результат инструмента
    W-->>H: ответ, заметки
    opt во втором вызове выбран update_record
        H->>S: вызов инструмента
    end
    H->>M: write, заметки Worker

    H->>M: context для Reviewer
    M-->>H: контекст
    H->>R: контекст и результат на проверку
    R-->>H: accept или reject, заметки
    H->>M: write, заметки Reviewer

    H->>E: проверки этой сессии
    E-->>H: пройдена или нет, метка провала

    H->>M: end_session
    Note over M: ours извлекает факты закрытой сессии
```

Номера шагов совпадают с номерами на схеме.

| Шаги | Что происходит | Код |
|---|---|---|
| 1 | запись сообщений и заметок сценария | [`live.py:131-135`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L131-L135) |
| 2–3 | контекст для Planner | [`live.py:141`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L141) |
| 4–5 | вызов Planner | [`live.py:142`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L142) |
| 6 | заметки Planner | [`live.py:143`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L143) |
| 7–8 | контекст для Worker, один на оба вызова | [`live.py:148`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L148) |
| 9–10 | первый вызов Worker | [`live.py:151`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L151) |
| 11–12 | чтение источника | [`live.py:154-155`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L154-L155) |
| 13 | запись источника как `untrusted` | [`live.py:156-162`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L156-L162) |
| 14–15 | `update_record` в первом вызове | [`live.py:163-164`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L163-L164) |
| 16–17 | второй вызов Worker | [`live.py:167`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L167) |
| 18 | `update_record` во втором вызове | [`live.py:169-171`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L169-L171) |
| 19 | заметки Worker | [`live.py:172`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L172) |
| 20–21 | контекст для Reviewer | [`live.py:176`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L176) |
| 22–23 | вызов Reviewer | [`live.py:177`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L177) |
| 24 | заметки Reviewer | [`live.py:178`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L178) |
| 25–26 | проверки и метки провалов | [`live.py:181-198`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L181-L198) |
| 27 | `end_session` | [`live.py:200-201`](https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/live.py#L200-L201) |

## 3. Память `ours`

Запись и чтение разделены. `write` только сохраняет запись; факты, ограничения и фрагменты появляются в `end_session`. Текущее значение не хранится: оно вычисляется при каждом чтении из версий, которые видит этот читатель, поэтому область видимости действует раньше разрешения конфликтов.

```mermaid
flowchart TB
    subgraph writing["Запись"]
        entry["write: запись сохраняется ↗"]
        close["end_session: записи сессии по порядку clock ↗"]
        extractor["Экстрактор ↗<br/>факты с датой и источником"]
        rule["rule_constraints ↗<br/>только доверенные записи"]
        guard["split_untrusted ↗<br/>разбор по строкам"]
        entry --> close
        close --> extractor
        close --> rule
        close -->|"недоверенные документы<br/>и выводы инструментов"| guard
    end

    subgraph stores["Хранилища"]
        versions["Версии фактов ↗<br/>по ключу entity и attribute"]
        constraints["Закреплённые ограничения ↗"]
        fragments["Фрагменты quoted_data ↗"]
        quarantine["Карантин ↗<br/>в контекст не попадает"]
    end

    extractor --> versions
    rule --> constraints
    guard -->|"значение не извлечено как факт"| fragments
    guard -->|"похоже на инструкцию"| quarantine

    subgraph reading["Чтение: context"]
        scope["Фильтр видимости ↗<br/>private, task, shared"]
        first["Ограничения идут первыми ↗<br/>ошибка, если не помещаются в лимит"]
        resolve["Факты ↗<br/>разрешение версий, метки DISPUTED и data"]
        rest["Фрагменты ↗"]
        rank["Отбор по BM25 и времени ↗<br/>сначала факты, затем фрагменты"]
        limit["Заполнение до 2000 токенов ↗"]
        scope --> first
        scope --> resolve
        scope --> rest
        resolve --> rank
        rest --> rank
        first --> limit
        rank --> limit
    end

    constraints --> scope
    versions --> scope
    fragments --> scope

    click entry href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/base.py#L28"
    click close href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L50-L54"
    click extractor href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/extract.py#L230"
    click rule href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/extract.py#L39"
    click guard href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/guard.py#L29"
    click versions href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L74-L76"
    click constraints href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L62-L64"
    click fragments href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L68-L70"
    click quarantine href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L71"
    click scope href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/base.py#L8"
    click first href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L169-L175"
    click resolve href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L140"
    click rest href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L180-L182"
    click rank href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L183-L185"
    click limit href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L186-L190"
```

Последующие итерации построены как подклассы `ours` в `scripts/` и не меняют `src/mam`:

| Вариант | Что добавлено | Код |
|---|---|---|
| `ours2` | буфер записей открытой сессии; остаток лимита заполняется старыми записями по BM25, кроме недоверенных и записей с проигравшими значениями; недоверенное значение новее доверенного показывается как спор | `scripts/post_hoc_ours2.py` |
| `ours3` | проигравшие значения заменяются на `[outdated]`, запись остаётся; заполнение до 300 токенов | `scripts/post_hoc_ours2.py` |
| `ours4` | экстрактор возвращает и ограничения; принимаются только из доверенных записей и объединяются с результатом правила | `scripts/post_hoc_ours4.py` |

Порядок под лимитом у `ours2`–`ours4`: ограничения, буфер, факты, фрагменты, заполнение.

## 4. Разрешение конфликта

Версии одного ключа обходятся в порядке записи (`_resolve`). Новая версия сравнивается с действующей: сначала по времени события, затем по авторитету источника (пользователь 3, инструмент 2, документ 1, агент 0).

```mermaid
flowchart TD
    next["Следующая видимая версия ключа ↗"] --> dated{"Время события ↗<br/>указано в тексте?"}
    dated -->|"нет"| assume["Считать её последней: ↗<br/>время = максимум + 1"]
    dated -->|"да"| same
    assume --> same{"Такое значение ↗<br/>уже действует?"}
    same -->|"да"| confirm["Значение остаётся, ↗<br/>сохраняется более доверенный источник"]
    same -->|"нет"| empty{"Есть действующее ↗<br/>значение?"}
    empty -->|"нет"| accept["Принять ↗"]
    empty -->|"да"| trust{"Версия untrusted, ↗<br/>а действующая нет?"}
    trust -->|"да"| rejectTrust["Отклонить: недоверенный источник ↗<br/>не меняет доверенный факт"]
    trust -->|"нет"| time{"Сравнить время события ↗"}
    time -->|"новее"| later["Заменить: later_event ↗"]
    time -->|"старше"| rejectOld["Отклонить: older event ↗"]
    time -->|"равно"| authority{"Сравнить авторитет ↗"}
    authority -->|"выше"| replace["Заменить: authority ↗"]
    authority -->|"ниже"| rejectLow["Отклонить: lower authority ↗"]
    authority -->|"равен"| disputed["Оставить оба значения: ↗<br/>DISPUTED"]

    click next href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L104"
    click dated href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L106"
    click assume href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L107"
    click same href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L109"
    click confirm href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L110-L112"
    click empty href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L113"
    click accept href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L114"
    click trust href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L115"
    click rejectTrust href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L116-L117"
    click time href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L120"
    click later href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L121-L122"
    click rejectOld href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L123-L124"
    click authority href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L125"
    click replace href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L126-L127"
    click rejectLow href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L128-L129"
    click disputed href "https://github.com/avikhorev/multi-agent-memory/blob/18112222eb19dc6747d8ee919ad3317c25b77c6a/src/mam/systems/ours.py#L130-L132"
```
