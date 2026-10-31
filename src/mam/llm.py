"""LLM transport: one narrow interface and two backends (the claude process and a scripted fake).

Every call is stateless: a new process, closed stdin, an empty working directory, a
whitelisted environment (docs/PILOT.md). Credentials in the environment are passed
unchanged and never logged.
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

MODEL = "claude-haiku-5-5"
PINNED_CLI_VERSION = "2.1.316"
ENV_WHITELIST = (
    "PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy",
    "NO_PROXY", "no_proxy", "NODE_EXTRA_CA_CERTS", "SSL_CERT_FILE",
    "ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_BASE_URL")
_LIMIT_MARKERS = ("rate limit", "429", "overloaded", "too many requests")
_REFUSAL_MARKER = "can't help with this"


class LLMError(Exception):
    """The call failed in a way that retrying will not fix."""


class InfrastructureError(Exception):
    """The environment is not as required (CLI missing, wrong version)."""


class RateLimitTimeout(Exception):
    """Rate limits lasted longer than the wait budget; the run should stop and resume later."""


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0
    cost_usd: float = 0.0


@dataclass(frozen=True)
class LLMResult:
    text: str
    usage: Usage
    latency_s: float
    refusal: bool = False


class LLMClient(Protocol):
    def complete(self, system: str, messages: list[dict], options: dict) -> LLMResult: ...


def default_runner(cmd, env, cwd, timeout):
    p = subprocess.run(cmd, env=env, cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                       timeout=timeout)
    return p.returncode, p.stdout, p.stderr


class ClaudeCliClient:
    def __init__(self, runner: Callable = default_runner, environ: dict | None = None,
                 sleep: Callable[[float], None] = time.sleep, max_wait_s: float = 1800, timeout_s: float = 180,
                 check_version: bool = True):
        self._runner = runner
        self._environ = dict(os.environ if environ is None else environ)
        self._sleep = sleep
        self.max_wait_s = max_wait_s
        self.timeout_s = timeout_s
        self.infra_log: list[dict] = []
        if check_version:
            self._check_version()

    def _env(self) -> dict:
        env = {k: v for k, v in self._environ.items() if k in ENV_WHITELIST}
        env["DISABLE_AUTOUPDATER"] = "1"
        return env

    def _check_version(self) -> None:
        try:
            rc, out, _ = self._runner(["claude", "--version"], self._env(), None, 30)
        except (OSError, subprocess.SubprocessError) as err:
            raise InfrastructureError(f"cannot run claude: {err}") from err
        found = out.split()[0] if rc == 0 and out.split() else ""
        if found != PINNED_CLI_VERSION:
            raise InfrastructureError(f"claude version {found or 'unknown'} found, {PINNED_CLI_VERSION} is pinned")

    def _command(self, system: str, prompt: str, options: dict) -> list[str]:
        return ["claude", "-p", "--model", MODEL, "--output-format", "json", "--system-prompt", system,
                "--tools", "", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
                "--setting-sources", "", "--disable-slash-commands", "--no-session-persistence",
                "--effort", options.get("effort", "low"), prompt]

    def complete(self, system: str, messages: list[dict], options: dict) -> LLMResult:
        if len(messages) != 1 or messages[0].get("role") != "user":
            raise ValueError("exactly one user message is required")
        cmd = self._command(system, messages[0]["content"], options)
        waited, delay = 0.0, 2.0
        while True:
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
                waited, delay = waited + delay, delay * 2
                continue
            u = data.get("usage") or {}
            usage = Usage(
                input_tokens=u.get("input_tokens") or 0, cache_creation_tokens=u.get("cache_creation_input_tokens") or 0,
                cache_read_tokens=u.get("cache_read_input_tokens") or 0, output_tokens=u.get("output_tokens") or 0,
                thinking_tokens=(u.get("output_tokens_details") or {}).get("thinking_tokens") or 0,
                cost_usd=float(data.get("total_cost_usd") or 0))
            if data.get("is_error"):
                if _REFUSAL_MARKER in text:
                    return LLMResult("", usage, latency, refusal=True)
                raise LLMError(f"model error: {text[:200]}")
            return LLMResult(text, usage, latency)


class FakeClient:
    """Scripted replies: a list consumed in order, or a function (system, messages) -> text or None (refusal)."""

    def __init__(self, replies):
        self._replies = replies
        self.calls: list[dict] = []

    def complete(self, system: str, messages: list[dict], options: dict) -> LLMResult:
        self.calls.append({"system": system, "messages": messages, "options": options})
        if callable(self._replies):
            text = self._replies(system, messages)
        elif self._replies:
            text = self._replies.pop(0)
        else:
            raise LLMError("the script of fake replies is exhausted")
        used = count(system) + sum(count(m["content"]) for m in messages)
        if text is None:
            return LLMResult("", Usage(input_tokens=used), 0.0, refusal=True)
        return LLMResult(text, Usage(input_tokens=used, output_tokens=count(text)), 0.0)
