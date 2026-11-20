"""Transport to the model: one narrow interface and two backends (the claude process and a scripted stub).

Each call is stateless: a new process, closed stdin, an empty working directory,
an environment from an allow-list (docs/PILOT.md). This is needed so that the answer is not affected by anything
except the prompt passed (neither files, nor past sessions, nor the user's settings).
Credentials from the environment are passed through unchanged and are not written to the journal.
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

MODEL = "claude-haiku-5-5"  # the model of all runs (one, so that results are comparable)
PINNED_CLI_VERSION = "2.1.316"  # the only allowed CLI version: another one may behave differently
# Environment variables allowed to be passed to the claude process: path, locale, proxy, certificates and credentials.
# Everything else is dropped, so that secrets do not leak and other people's settings do not affect the run.
ENV_WHITELIST = (
    "PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy",
    "NO_PROXY", "no_proxy", "NODE_EXTRA_CA_CERTS", "SSL_CERT_FILE",
    "ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_BASE_URL")
# Signs that the rate limit was hit (then we wait and retry).
_LIMIT_MARKERS = ("rate limit", "429", "overloaded", "too many requests")
# The phrase by which we tell a model refusal from an ordinary error.
_REFUSAL_MARKER = "can't help with this"


class LLMError(Exception):
    """The call failed in a way that a retry will not fix."""


class InfrastructureError(Exception):
    """The environment does not meet the requirements (no CLI or the wrong version)."""


class RateLimitTimeout(Exception):
    """Rate limits lasted longer than the waiting budget; the run must be stopped and continued later."""


@dataclass(frozen=True)
class Usage:
    """Usage of one call: tokens by kind and cost."""
    input_tokens: int = 0  # ordinary input tokens
    cache_creation_tokens: int = 0  # input tokens written to the prompt cache (more expensive than ordinary ones)
    cache_read_tokens: int = 0  # input tokens read from the cache (cheaper)
    output_tokens: int = 0  # answer tokens
    thinking_tokens: int = 0  # part of the answer spent on reasoning
    cost_usd: float = 0.0  # cost reported by the provider


@dataclass(frozen=True)
class LLMResult:
    """Result of a model call."""
    text: str  # answer text; empty on refusal
    usage: Usage  # usage
    latency_s: float  # call time in seconds
    refusal: bool = False  # the model refused to answer


class LLMClient(Protocol):
    """Everything the rest of the code needs from the model: one function. This makes the real client easy to replace with a stub in tests."""
    def complete(self, system: str, messages: list[dict], options: dict) -> LLMResult: ...


def default_runner(cmd, env, cwd, timeout):
    """Starts the process and returns (exit code, stdout, stderr). Kept separate so that tests can replace the launch."""
    p = subprocess.run(cmd, env=env, cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                       timeout=timeout)
    return p.returncode, p.stdout, p.stderr


class ClaudeCliClient:
    """Client via the CLI `claude -p`. Dependencies (launch, environment, sleep) are injected as parameters for the tests."""
    def __init__(self, runner: Callable = default_runner, environ: dict | None = None,
                 sleep: Callable[[float], None] = time.sleep, max_wait_s: float = 1800, timeout_s: float = 180,
                 check_version: bool = True):
        self._runner = runner  # how to run the process
        self._environ = dict(os.environ if environ is None else environ)
        self._sleep = sleep  # how to wait when rate-limited
        self.max_wait_s = max_wait_s  # how long in total we are willing to wait because of limits
        self.timeout_s = timeout_s  # ceiling on the time of one call
        self.infra_log: list[dict] = []  # infrastructure events (rate-limit waits) for the report
        if check_version:
            self._check_version()

    def _env(self) -> dict:
        """Environment of the process: only variables from the allow-list."""
        env = {k: v for k, v in self._environ.items() if k in ENV_WHITELIST}
        env["DISABLE_AUTOUPDATER"] = "1"  # forbid self-update: the version must stay pinned
        return env

    def _check_version(self) -> None:
        """Checks the CLI version against the pinned one: another version may change the results."""
        try:
            rc, out, _ = self._runner(["claude", "--version"], self._env(), None, 30)
        except (OSError, subprocess.SubprocessError) as err:
            raise InfrastructureError(f"cannot run claude: {err}") from err
        found = out.split()[0] if rc == 0 and out.split() else ""
        if found != PINNED_CLI_VERSION:
            raise InfrastructureError(f"claude version {found or 'unknown'} found, {PINNED_CLI_VERSION} is pinned")

    def _command(self, system: str, prompt: str, options: dict) -> list[str]:
        """Launch command. All flags cut off the influence of the outside world: no tools (--tools ""),
        no MCP, no user settings or commands, no session saving."""
        return ["claude", "-p", "--model", MODEL, "--output-format", "json", "--system-prompt", system,
                "--tools", "", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
                "--setting-sources", "", "--disable-slash-commands", "--no-session-persistence",
                "--effort", options.get("effort", "low"), prompt]

    def complete(self, system: str, messages: list[dict], options: dict) -> LLMResult:
        """One model call. Rate limits are waited out with doubling pauses until the max_wait_s budget runs out."""
        if len(messages) != 1 or messages[0].get("role") != "user":
            raise ValueError("exactly one user message is required")
        cmd = self._command(system, messages[0]["content"], options)
        waited, delay = 0.0, 2.0  # how long we have already waited and how long to wait next time
        while True:
            # An empty temporary directory for each call: the model must not see the project's files.
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
                waited, delay = waited + delay, delay * 2  # exponential pause
                continue
            u = data.get("usage") or {}
            usage = Usage(
                input_tokens=u.get("input_tokens") or 0, cache_creation_tokens=u.get("cache_creation_input_tokens") or 0,
                cache_read_tokens=u.get("cache_read_input_tokens") or 0, output_tokens=u.get("output_tokens") or 0,
                thinking_tokens=(u.get("output_tokens_details") or {}).get("thinking_tokens") or 0,
                cost_usd=float(data.get("total_cost_usd") or 0))
            if data.get("is_error"):
                # A refusal is a normal outcome (it is counted in the metrics); other errors are failures.
                if _REFUSAL_MARKER in text:
                    return LLMResult("", usage, latency, refusal=True)
                raise LLMError(f"model error: {text[:200]}")
            return LLMResult(text, usage, latency)


class FakeClient:
    """A stub with prepared answers: a list returned in order, or a function (system, messages) -> text or None (refusal).
    Needed for tests and for offline runs without network."""

    def __init__(self, replies):
        self._replies = replies
        self.calls: list[dict] = []  # journal of calls, so that tests can check exactly what was sent

    def complete(self, system: str, messages: list[dict], options: dict) -> LLMResult:
        self.calls.append({"system": system, "messages": messages, "options": options})
        if callable(self._replies):
            text = self._replies(system, messages)
        elif self._replies:
            text = self._replies.pop(0)
        else:
            raise LLMError("the script of fake replies is exhausted")
        # Input tokens are counted by our own counter, so that cost accounting works without the network.
        used = count(system) + sum(count(m["content"]) for m in messages)
        if text is None:
            return LLMResult("", Usage(input_tokens=used), 0.0, refusal=True)
        return LLMResult(text, Usage(input_tokens=used, output_tokens=count(text)), 0.0)
