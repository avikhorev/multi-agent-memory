# Запуск и воспроизведение

Все команды выполняются из корня репозитория. Основной результат записан в `results/live/main`; **новые прогоны не должны его перезаписывать**.

## 1. Установка и тесты

**Docker** (Python, Node.js и закреплённый Claude Code внутри образа):

```bash
make docker-test
make docker-reproduce
```

Сборка Docker-образа требует скачивания зависимостей при первом запуске. Тесты и пересчёт таблиц не вызывают LLM; после сборки образа пересчёт работает без доступа к модели.

**Локально** (Python 3.11+):

```bash
make venv
make test
make reproduce
```

Для команд Python вне `make` активируйте виртуальное окружение (`. .venv/bin/activate`), чтобы были доступны зависимости проекта.

## 2. Воспроизведение без модели

| Задача | Команда | Результат |
|---|---|---|
| Пересчитать уровень памяти на `eval` и `holdout`, а также таблицы живого слоя | `make reproduce` | `results/memory_level/`, `results/live/main/tables.md` |
| Пересчитать один сплит | `make memory-level SPLIT=eval` | `results/memory_level/eval/` |
| Заново собрать живые таблицы | `make live-tables DIR=results/live/main` | `results/live/main/tables.md` |
| Сгенерировать сценарии | `make dataset` | `data/dev/`, `data/eval/`, `holdout/` |
| Посмотреть трассу сценария | `PYTHONPATH=src python -m mam.run trace C1-eval-0003 --dir results/live/main` | Трасса в терминале |

Проверка изменений после пересчёта:

```bash
git diff --stat results
```

Сценарии детерминированы на Python 3.11–3.13. При `make reproduce` различаются измерения в `timing/`; на Python 3.11 возможна ещё одна разница в нижней границе интервала для `rolling_summary@cache` (1086 → 1087 в `results/memory_level/eval/tables.md`). Остальное должно совпасть с сохранёнными файлами.

## 3. Живой слой: платный запуск

Для вызовов модели требуются Node.js 18+, Claude Code **2.1.316** и один из способов авторизации:

| Способ | Настройка | Что проверено в проекте |
|---|---|---|
| API-ключ | `ANTHROPIC_API_KEY` | Не проверен |
| Токен подписки | `claude setup-token`, затем `CLAUDE_CODE_OAUTH_TOKEN` | Короткий прогон в Docker |
| Интерактивный вход | `claude` | Не проверен |

Ключи и токены передаются процессу модели, но не сохраняются и не печатаются. Установите Claude Code локально, если не используете Docker:

```bash
npm install -g @anthropic-ai/claude-code@2.1.316
make doctor
make live SIZE=smoke REPEATS=1 MAX_COST=0.5
```

`make live` записывает результат в `results/live/rerun` по умолчанию. Чтобы использовать другой каталог, задайте `OUT=results/live/experiment`; повторный запуск с тем же `OUT` пропускает готовые единицы.

| Параметр | По умолчанию | Назначение |
|---|---|---|
| `SIZE` | `A` | Размер выборки: `A` или `B` (см. [D21](DECISIONS.md#d21)) |
| `REPEATS` | `2` | Повторы единиц |
| `WORKERS` | `8` | Параллельные вызовы |
| `MAX_COST` | `10` | Мягкий предел стоимости, USD |
| `OUT` | `results/live/rerun` | Каталог результатов нового прогона |

Предел стоимости **мягкий**: начатые единицы завершаются, поэтому итог может превысить `MAX_COST`. Код завершения `2` при остановке по лимиту — ожидаемое поведение, а не ошибка модели. Таблицы: `make live-tables DIR=results/live/rerun`.

Проверенный короткий прогон в Docker: 22 из 35 единиц, без сбоев, $0,519 (`results/live/docker_check`). Полный живой прогон в Docker и запуск по API-ключу не выполнялись. Это проверка работоспособности запуска, а не воспроизведение чисел отчёта.

## 4. Извлечение фактов

`make extraction` обращается к модели и сохраняет ответы в `results/extraction/`; `make extraction-trial` запускает короткий вариант. Сохранённые кеши используются при пересчёте уровня памяти без LLM.

Качество извлечения по сохранённому кешу можно пересчитать без модели:

```bash
PYTHONPATH=src python -m mam.extraction_quality results/extraction/eval/cache.jsonl data/eval
```

Результат сравнивайте с `results/extraction/eval/quality.md`.

## 5. Дополнительные проверки (*post hoc*)

Основные цифры находятся в [`REPORT.md`](../REPORT.md), разделы 5–9. Следующие проверки проведены **после** заморозки, их нельзя смешивать с первоначальным сравнением. Для скриптов требуется активированное виртуальное окружение и `PYTHONPATH=src`. Если в ячейке перечислено несколько подкоманд (`compare`, `criteria` и т. п.), используйте для каждой тот же путь к скрипту.

| Что проверить | Запуск без модели / подготовка | Платный этап, если есть |
|---|---|---|
| Подача истории с автором и сессией | `python scripts/post_hoc_presentation.py plan`, затем `counts`, `blind`, `join` | `python scripts/post_hoc_presentation.py run --max-cost-usd 1.5` |
| Контрольный повтор | `python scripts/post_hoc_control_repeat.py` | Сами единицы повтора уже сохранены |
| Зависимость разрешения конфликта от порядка записей | `python scripts/post_hoc_write_order.py` | Нет |
| Дополнительные контроли C1/C3 | `python scripts/post_hoc_c1c3.py lenient` и `python scripts/post_hoc_controls.py` | Нет |
| `ours2` и `ours3` | `python scripts/post_hoc_ours2.py memory`, `compare`, `memory3`, `compare3` | `live --variant ours2_lite` / `live --variant ours3` |
| Новые сценарии и перефразирование | `python scripts/post_hoc_fresh.py plan`; `python scripts/post_hoc_paraphrase.py compare` | `post_hoc_fresh.py run`; `post_hoc_paraphrase.py run` |
| `ours4` | `pytest scripts/test_post_hoc_ours4.py`; `python scripts/post_hoc_ours4.py criteria` (по сохранённым результатам) | `python scripts/post_hoc_ours4.py paraphrase`, затем `runA`, `runB` |
| Внешние Mem0 и Graphiti | `python external/run.py <система> tables` | `python external/run.py <система> pilot` или `run` |

У скриптов есть дополнительные подкоманды (`criteria`, `classified` и др.). Точный порядок, критерии и каталоги выходных данных указаны в разделах 11–15 [`REPORT.md`](../REPORT.md) и в `results/post_hoc/`. Для внешних систем нужны отдельные окружения с зависимостями `external/requirements-<система>.txt`.
