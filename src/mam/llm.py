"""Транспорт к модели: один узкий интерфейс и два бэкенда (процесс claude и сценарная заглушка).

Каждый вызов не имеет состояния: новый процесс, закрытый stdin, пустой рабочий каталог,
окружение из белого списка (docs/PILOT.md). Это нужно, чтобы на ответ не влияло ничего,
кроме переданного промпта (ни файлы, ни прошлые сессии, ни настройки пользователя).
Учётные данные из окружения передаются без изменений и не пишутся в журнал.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from typing import Callable, Protocol

from mam.tokens import count

MODEL = "claude-haiku-5-5"  # модель всех прогонов (одна, чтобы результаты сравнивались)
PINNED_CLI_VERSION = "2.1.316"  # единственная допустимая версия CLI: другая может вести себя иначе
# Переменные окружения, которые разрешено передать процессу claude: путь, локаль, прокси, сертификаты и учётные данные.
# Всё остальное отбрасывается, чтобы не утекли секреты и не повлияли чужие настройки.
ENV_WHITELIST = (
    "PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy",
    "NO_PROXY", "no_proxy", "NODE_EXTRA_CA_CERTS", "SSL_CERT_FILE",
    "ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_BASE_URL")
# Признаки того, что упёрлись в ограничение частоты запросов (тогда ждём и повторяем).
_LIMIT_MARKERS = ("rate limit", "429", "overloaded", "too many requests")
# Фраза, по которой отличаем отказ модели от обычной ошибки.
_REFUSAL_MARKER = "can't help with this"


class LLMError(Exception):
    """Вызов провалился так, что повтор не поможет."""


class InfrastructureError(Exception):
    """Окружение не соответствует требованиям (нет CLI или не та версия)."""


class RateLimitTimeout(Exception):
    """Ограничения частоты длились дольше бюджета ожидания; прогон нужно остановить и продолжить позже."""


@dataclass(frozen=True)
class Usage:
    """Расход одного вызова: токены по видам и стоимость."""
    input_tokens: int = 0  # обычные входные токены
    cache_creation_tokens: int = 0  # входные токены, записанные в кеш промпта (дороже обычных)
    cache_read_tokens: int = 0  # входные токены, прочитанные из кеша (дешевле)
    output_tokens: int = 0  # токены ответа
    thinking_tokens: int = 0  # часть ответа, потраченная на рассуждения
    cost_usd: float = 0.0  # стоимость, которую сообщил провайдер


@dataclass(frozen=True)
class LLMResult:
    """Результат вызова модели."""
    text: str  # текст ответа; пустой при отказе
    usage: Usage  # расход
    latency_s: float  # время вызова в секундах
    refusal: bool = False  # модель отказалась отвечать


class LLMClient(Protocol):
    """Всё, что нужно остальному коду от модели: одна функция. Так реальный клиент легко заменить заглушкой в тестах."""
    def complete(self, system: str, messages: list[dict], options: dict) -> LLMResult: ...


def default_runner(cmd, env, cwd, timeout):
    """Запускает процесс и возвращает (код выхода, stdout, stderr). Вынесено отдельно, чтобы тесты подменяли запуск."""
    p = subprocess.run(cmd, env=env, cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                       timeout=timeout)
    return p.returncode, p.stdout, p.stderr


class ClaudeCliClient:
    """Клиент через CLI `claude -p`. Зависимости (запуск, окружение, сон) внедряются параметрами ради тестов."""
    def __init__(self, runner: Callable = default_runner, environ: dict | None = None,
                 sleep: Callable[[float], None] = time.sleep, max_wait_s: float = 1800, timeout_s: float = 180,
                 check_version: bool = True):
        self._runner = runner  # как запускать процесс
        self._environ = dict(os.environ if environ is None else environ)
        self._sleep = sleep  # как ждать при ограничении частоты
        self.max_wait_s = max_wait_s  # сколько всего готовы ждать из-за лимитов
        self.timeout_s = timeout_s  # потолок времени одного вызова
        self.infra_log: list[dict] = []  # события инфраструктуры (ожидания лимитов) для отчёта
        if check_version:
            self._check_version()

    def _env(self) -> dict:
        """Окружение процесса: только переменные из белого списка."""
        env = {k: v for k, v in self._environ.items() if k in ENV_WHITELIST}
        env["DISABLE_AUTOUPDATER"] = "1"  # запрет самообновления: версия должна оставаться закреплённой
        return env

    def _check_version(self) -> None:
        """Сверяет версию CLI с закреплённой: иная версия может изменить результаты."""
        try:
            rc, out, _ = self._runner(["claude", "--version"], self._env(), None, 30)
        except (OSError, subprocess.SubprocessError) as err:
            raise InfrastructureError(f"cannot run claude: {err}") from err
        found = out.split()[0] if rc == 0 and out.split() else ""
        if found != PINNED_CLI_VERSION:
            raise InfrastructureError(f"claude version {found or 'unknown'} found, {PINNED_CLI_VERSION} is pinned")

    def _command(self, system: str, prompt: str, options: dict) -> list[str]:
        """Команда запуска. Все флаги отрезают влияние внешнего мира: без инструментов (--tools ""),
        без MCP, без пользовательских настроек и команд, без сохранения сессии."""
        return ["claude", "-p", "--model", MODEL, "--output-format", "json", "--system-prompt", system,
                "--tools", "", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
                "--setting-sources", "", "--disable-slash-commands", "--no-session-persistence",
                "--effort", options.get("effort", "low"), prompt]

    def complete(self, system: str, messages: list[dict], options: dict) -> LLMResult:
        """Один вызов модели. Лимиты частоты ждём с удвоением паузы, пока не выйдет бюджет max_wait_s."""
        if len(messages) != 1 or messages[0].get("role") != "user":
            raise ValueError("exactly one user message is required")
        cmd = self._command(system, messages[0]["content"], options)
        waited, delay = 0.0, 2.0  # сколько уже ждали и сколько ждать в следующий раз
        while True:
            # Пустой временный каталог на каждый вызов: модель не должна видеть файлы проекта.
            with tempfile.TemporaryDirectory() as cwd:
                t0 = time.monotonic()
                try:
                    rc, out, err = self._runner(cmd, self._env(), cwd, self.timeout_s)
                except subprocess.TimeoutExpired as e:
                    raise LLMError("the claude process timed out") from e
                latency = time.monotonic() - t0
            try:
                data = json.loads(out)
            except json.JSONDecodeError as e:
                raise LLMError(f"unparseable output (exit {rc}): {out[:100]!r} {err[:100]!r}") from e
            text = str(data.get("result", ""))
            if data.get("is_error") and any(m in text.lower() for m in _LIMIT_MARKERS):
                if waited + delay > self.max_wait_s:
                    raise RateLimitTimeout(f"rate limited for {waited:.0f} s")
                self.infra_log.append({"kind": "rate_limit", "wait_s": delay})
                self._sleep(delay)
                waited, delay = waited + delay, delay * 2  # экспоненциальная пауза
                continue
            u = data.get("usage") or {}
            usage = Usage(
                input_tokens=u.get("input_tokens") or 0, cache_creation_tokens=u.get("cache_creation_input_tokens") or 0,
                cache_read_tokens=u.get("cache_read_input_tokens") or 0, output_tokens=u.get("output_tokens") or 0,
                thinking_tokens=(u.get("output_tokens_details") or {}).get("thinking_tokens") or 0,
                cost_usd=float(data.get("total_cost_usd") or 0))
            if data.get("is_error"):
                # Отказ — штатный исход (его считаем в метриках), прочие ошибки — сбой.
                if _REFUSAL_MARKER in text:
                    return LLMResult("", usage, latency, refusal=True)
                raise LLMError(f"model error: {text[:200]}")
            return LLMResult(text, usage, latency)


class FakeClient:
    """Заглушка с заготовленными ответами: список, выдаваемый по порядку, или функция (system, messages) -> текст или None (отказ).
    Нужна для тестов и для офлайн-прогонов без сети."""

    def __init__(self, replies):
        self._replies = replies
        self.calls: list[dict] = []  # журнал вызовов, чтобы тесты могли проверить, что именно отправили

    def complete(self, system: str, messages: list[dict], options: dict) -> LLMResult:
        self.calls.append({"system": system, "messages": messages, "options": options})
        if callable(self._replies):
            text = self._replies(system, messages)
        elif self._replies:
            text = self._replies.pop(0)
        else:
            raise LLMError("the script of fake replies is exhausted")
        # Входные токены считаем своим счётчиком, чтобы учёт стоимости работал и без сети.
        used = count(system) + sum(count(m["content"]) for m in messages)
        if text is None:
            return LLMResult("", Usage(input_tokens=used), 0.0, refusal=True)
        return LLMResult(text, Usage(input_tokens=used, output_tokens=count(text)), 0.0)
