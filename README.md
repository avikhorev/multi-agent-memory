# Память для мультиагентной системы: реализация и бенчмарк

Несколько агентов (Planner, Worker, Reviewer) ведут длинную задачу, например сопровождают проект клиента на протяжении 10–30 сессий. Между сессиями и между агентами теряется контекст. Здесь реализована структурированная память (`ours`), четыре базовые линии (полная история, скользящее окно, скользящее резюме, поиск BM25) и бенчмарк, который измеряет, где память лучше простых подходов, а где нет.

- Постановка, метрики и гипотезы проигрыша: [`docs/PROBLEM.md`](docs/PROBLEM.md); модель угроз: [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md); допущения: [`docs/ASSUMPTIONS.md`](docs/ASSUMPTIONS.md).
- Формат сценариев, правила оценки и интерфейс памяти: [`docs/SCENARIO_FORMAT.md`](docs/SCENARIO_FORMAT.md).
- Принятые решения с числами: [`docs/DECISIONS.md`](docs/DECISIONS.md); измерения вызова модели: [`docs/PILOT.md`](docs/PILOT.md).
- Отчёт с результатами: [`REPORT.md`](REPORT.md).

## Быстрый старт: одна команда на задачу

Нужен Docker. Всё остальное внутри образа (Python 3.11, Node.js, Claude Code 2.1.316).

```bash
make docker-test        # тесты, без модели
```

```bash
make docker-reproduce   # уровень памяти и все таблицы из сохранённых результатов, без модели и без сети
```

```bash
ANTHROPIC_API_KEY=... make docker-live   # живой слой с настоящими агентами, платный; пишет в results/live/rerun
```

Новые прогоны идут в `results/live/rerun` (переменная `OUT`); каталог `results/live/main` содержит закоммиченный прогон отчёта и только читается. Таблицы нового прогона: `make live-tables DIR=results/live/rerun`.

Без Docker: Python 3.11 или новее, затем `make venv`, после чего те же цели без префикса `docker-`: `make test`, `make reproduce`, `make live`. Для `make live` понадобятся ещё Node.js 18 или новее и закреплённая версия Claude Code:

```bash
npm install -g @anthropic-ai/claude-code@2.1.316
```

Сборка образа, `make docker-test` (419 passed) и `make docker-reproduce` без сети проверены на Python 3.11.9. `make docker-live` и запуск по ключу и по подписке: NOT RUN.

## Доступ к модели (только для живого слоя и прохода извлечения)

Тесты, `make reproduce` и уровень памяти модель не вызывают. Для всего остального нужен один из способов:

| Способ | Что сделать | Статус проверки |
|---|---|---|
| Ключ API (оплата по ключу) | задать `ANTHROPIC_API_KEY` | в этом репозитории не проверялся (ключа не было) |
| Подписка | один раз выполнить `claude setup-token`, передать выданный токен в `CLAUDE_CODE_OAUTH_TOKEN` | не проверено |
| Вход в `claude` на этой машине | выполнить `claude` и войти | не проверено |

Значения ключа и токена передаются процессу модели без изменений и нигде не печатаются и не сохраняются (в манифесте единицы работы записано только `api_key_set: true/false`). Проверка доступа: `make doctor`; она возвращает код 78 и подсказку, если модель недоступна. Модель одна для всех агентов и для извлечения фактов: `claude-haiku-5-5`.

## Что воспроизводится и как

| Что | Как | Совпадение |
|---|---|---|
| Сценарии | `make dataset` | побайтно (Python 3.11–3.13) |
| Уровень памяти | `make reproduce` | побайтно, кроме файлов `timing/` (замеры времени) и одной ячейки `results/memory_level/eval/tables.md` на Python 3.11 (нижняя граница интервала `rolling_summary@cache`, 1086 → 1087) |
| Проход извлечения | `make extraction` (платный) | ответы модели сохранены в `results/extraction/`, их можно проигрывать без модели |
| Живой слой | `make live` (платный) | в пределах разброса: температура не задаётся, разброс оценивается повторами |
| Таблицы живого слоя | `make live-tables DIR=results/live/main` | побайтно из сохранённых единиц |
| Качество извлечения | `PYTHONPATH=src python -m mam.extraction_quality results/extraction/eval/cache.jsonl data/eval` (без модели) | совпадает с `results/extraction/eval/quality.md` |
| Проверка подачи с префиксом «сессия, автор, вид» (платная для `run`) | `PYTHONPATH=src python scripts/post_hoc_presentation.py plan` (список 48 единиц, без модели); `... run --max-cost-usd 1.5` (платный, пишет в `results/post_hoc/presentation`); `... counts`, `blind`, `join` (разбор сохранённых результатов, без модели) | `counts.md`, `classified.md` |
| Сравнение контрольного повтора с основным прогоном | `PYTHONPATH=src python scripts/post_hoc_control_repeat.py` (без модели) | совпадает с `results/post_hoc/control_repeat.md` |
| Итерация `ours2` (post hoc), уровень памяти | `PYTHONPATH=src python scripts/post_hoc_ours2.py memory` и `... compare` (без модели); тесты: `pytest scripts/test_post_hoc_ours2.py`; живой слой (платный): `... live --variant ours2_lite`, критерии `... criteria --variant ours2_lite`; `ours3`: `... memory3`, `... compare3` (без модели); живой слой (платный): `... live --variant ours3`, критерии `... criteria --variant ours3` | совпадает с `results/post_hoc/ours2/` |
| Проверка на новых данных (платная) | `PYTHONPATH=src python scripts/post_hoc_fresh.py plan` (без модели), `... run`, `... criteria`; `scripts/post_hoc_paraphrase.py paraphrase`, `run`, `compare` | `results/post_hoc/fresh/`, `results/post_hoc/paraphrase/` |
| Итерация `ours4` (закрепление ограничений моделью, платная) | `pytest scripts/test_post_hoc_ours4.py` (без модели); `PYTHONPATH=src python scripts/post_hoc_ours4.py paraphrase`, `runA`, `runB`, `criteria` | `results/post_hoc/paraphrase2/`, `results/post_hoc/ours4/` |
| Дополнительный разбор после заморозки | `python scripts/post_hoc_c1c3.py lenient`, `python scripts/post_hoc_controls.py` (без модели) | совпадает с `results/post_hoc/` |

После `make reproduce` сравните результат с закоммиченным: `git diff --stat results`. Различаться могут только файлы с замерами времени.

Если прогон остановлен по стоимости, `make live` завершается кодом 2 и `make` печатает `Error 2`: это штатный выход, не сбой. Предел `MAX_COST` мягкий: единицы, уже начатые к моменту остановки, доделываются, поэтому итог может немного превысить предел. Живой прогон возобновляется: после прерывания достаточно запустить `make live` снова с тем же `OUT`, готовые единицы работы пропускаются. Параметры: `SIZE` (размер выборки, см. [`docs/DECISIONS.md`](docs/DECISIONS.md)), `REPEATS` (повторы, по умолчанию 2), `WORKERS` (параллельные вызовы, по умолчанию 8), `MAX_COST` (предел стоимости в долларах, по умолчанию 10; считается по `total_cost_usd` из ответов, при оплате по ключу это реальные деньги).

## Структура

| Путь | Что там |
|---|---|
| `src/mam/` | код: типы, генератор сценариев, оценка, системы памяти (`systems/`), агенты, живой цикл, раннер, проход извлечения, таблицы |
| `tests/acceptance/` | приёмочные тесты по `docs/SCENARIO_FORMAT.md` |
| `tests/unit/` | юнит-тесты |
| `data/dev/`, `data/eval/` | сгенерированные сценарии (`dev` для отладки, `eval` для результатов) |
| `holdout/` | трудные сценарии, не использованные при настройке; результат показывается отдельной строкой |
| `results/pilot/` | измерения вызова модели |
| `results/extraction/` | сохранённые ответы модели при извлечении фактов и резюме |
| `results/memory_level/` | результаты уровня памяти и таблицы |
| `results/live/` | единицы работы живого слоя, трассы, таблицы |
| `results/mutation/` | сводка мутационного прохода |

Трассу любого сценария живого слоя можно вывести командой `python -m mam.run trace <id сценария> --dir results/live/main`.

## Ограничения

Выборка живого слоя мала: видны только крупные эффекты, поэтому для него приведены доли и диапазоны, а не доверительные интервалы. Фильтр доверия подстраивался под формулировки `dev`, общие с `eval`, поэтому независимой проверкой служит `holdout/`. Подробности, провалы с трассами и что делать дальше: [`REPORT.md`](REPORT.md).

## Лицензия

MIT, см. [`LICENSE`](LICENSE).
