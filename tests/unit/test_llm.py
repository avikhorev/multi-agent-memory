"""LLMClient through its public interface. The external boundary (the claude process) is replaced."""
import json

import pytest

from mam.llm import (ClaudeCliClient, FakeClient, InfrastructureError, LLMError, PINNED_CLI_VERSION,
                     RateLimitTimeout)

OK = {"is_error": False, "result": "OK", "total_cost_usd": 0.0005, "duration_api_ms": 1200,
      "usage": {"input_tokens": 2, "cache_creation_input_tokens": 600, "cache_read_input_tokens": 1000,
                "output_tokens": 40, "output_tokens_details": {"thinking_tokens": 25}}}
REFUSAL = {"is_error": True, "result": "API Error: Haiku 5.5 can't help with this. Start a new session to continue.",
           "total_cost_usd": 0.0002, "usage": {"input_tokens": 4, "cache_creation_input_tokens": 600,
                                               "cache_read_input_tokens": 600, "output_tokens": 0}}
LIMIT = {"is_error": True, "result": "API Error: 429 rate limit reached, try again later", "usage": {}}


class Runner:
    """Scripted stand-in for the claude process. Records every invocation."""

    def __init__(self, replies, version=PINNED_CLI_VERSION):
        self.replies, self.calls, self.version = list(replies), [], version

    def __call__(self, cmd, env, cwd, timeout):
        self.calls.append({"cmd": cmd, "env": env, "cwd": cwd})
        if cmd[:2] == ["claude", "--version"]:
            return 0, f"{self.version} (Claude Code)\n", ""
        reply = self.replies.pop(0)
        return 0, json.dumps(reply), ""


def client(replies, environ=None, sleeps=None, **kw):
    runner = Runner(replies, kw.pop("version", PINNED_CLI_VERSION))
    sleeps = sleeps if sleeps is not None else []
    return ClaudeCliClient(runner=runner, environ=environ or {"PATH": "/bin", "HOME": "/h", "SECRET_X": "s"},
                           sleep=sleeps.append, **kw), runner, sleeps


MSG = [{"role": "user", "content": "hello"}]


def test_a_call_returns_text_usage_cost_and_latency():
    c, _, _ = client([OK])
    r = c.complete("be brief", MSG, {})
    assert r.text == "OK" and not r.refusal
    u = r.usage
    assert (u.input_tokens, u.cache_creation_tokens, u.cache_read_tokens, u.output_tokens, u.thinking_tokens) == (2, 600, 1000, 40, 25)
    assert u.cost_usd == 0.0005 and r.latency_s >= 0


def test_the_command_has_the_pilot_flags_and_nothing_extra():
    c, runner, _ = client([OK])
    c.complete("sys prompt", MSG, {})
    cmd = [x for x in runner.calls if x["cmd"][1] == "-p"][0]["cmd"]
    assert cmd[:2] == ["claude", "-p"] and cmd[-1] == "hello"
    for flag in ("--no-session-persistence", "--disable-slash-commands", "--strict-mcp-config"):
        assert flag in cmd
    assert cmd[cmd.index("--system-prompt") + 1] == "sys prompt"
    assert cmd[cmd.index("--tools") + 1] == "" and cmd[cmd.index("--effort") + 1] == "low"
    assert cmd[cmd.index("--model") + 1] == "claude-haiku-5-5" and cmd[cmd.index("--setting-sources") + 1] == ""
    assert "--bare" not in cmd and "--thinking" not in cmd
    assert "--json-schema" not in cmd


def test_a_schema_option_adds_the_json_schema_flag_and_the_structured_object_is_kept():
    schema = '{"type": "object"}'
    c, runner, _ = client([{"is_error": False, "result": "{}", "structured_output": {"tool": "none"},
                            "total_cost_usd": 0.0, "duration_api_ms": 1, "usage": {}}])
    res = c.complete("sys prompt", MSG, {"schema": schema})
    cmd = [x for x in runner.calls if x["cmd"][1] == "-p"][0]["cmd"]
    assert cmd[cmd.index("--json-schema") + 1] == schema and cmd[-1] == "hello"
    assert res.parsed == {"tool": "none"}


def test_the_child_environment_is_a_whitelist_and_passes_credentials_unchanged():
    c, runner, _ = client([OK], environ={"PATH": "/bin", "HOME": "/h", "ANTHROPIC_API_KEY": "k1", "SECRET_X": "s",
                                         "MAX_THINKING_TOKENS": "1"})
    c.complete("s", MSG, {})
    env = [x for x in runner.calls if x["cmd"][1] == "-p"][0]["env"]
    assert env["ANTHROPIC_API_KEY"] == "k1" and env["DISABLE_AUTOUPDATER"] == "1"
    assert "SECRET_X" not in env and "MAX_THINKING_TOKENS" not in env


def test_each_call_runs_in_an_empty_directory():
    c, runner, _ = client([OK])
    c.complete("s", MSG, {})
    cwd = [x for x in runner.calls if x["cmd"][1] == "-p"][0]["cwd"]
    assert cwd and cwd != "."


def test_a_refusal_is_a_result_not_an_exception():
    c, _, _ = client([REFUSAL])
    r = c.complete("s", MSG, {})
    assert r.refusal and r.text == "" and r.usage.cost_usd == 0.0002


def test_rate_limits_are_retried_with_exponential_waits_and_logged_apart():
    c, _, sleeps = client([LIMIT, LIMIT, OK])
    r = c.complete("s", MSG, {})
    assert r.text == "OK" and sleeps == [2, 4]
    assert [e["kind"] for e in c.infra_log] == ["rate_limit", "rate_limit"]
    assert r.usage.cost_usd == 0.0005  # waits are not part of the call's metrics


def test_waiting_longer_than_the_budget_stops_the_run():
    c, _, _ = client([LIMIT] * 20, max_wait_s=10)
    with pytest.raises(RateLimitTimeout):
        c.complete("s", MSG, {})


def test_the_pinned_cli_version_is_checked_at_start():
    with pytest.raises(InfrastructureError):
        client([OK], version="9.9.9")


def test_exactly_one_user_message_is_required():
    c, _, _ = client([OK])
    with pytest.raises(ValueError):
        c.complete("s", [], {})
    with pytest.raises(ValueError):
        c.complete("s", MSG + MSG, {})


def test_unparseable_output_is_an_error():
    class Bad(Runner):
        def __call__(self, cmd, env, cwd, timeout):
            return (0, "SEGFAULT", "") if cmd[1] == "-p" else super().__call__(cmd, env, cwd, timeout)
    c = ClaudeCliClient(runner=Bad([]), environ={"PATH": "/bin"}, sleep=lambda s: None)
    with pytest.raises(LLMError):
        c.complete("s", MSG, {})


def test_fake_client_replays_scripted_replies_and_counts_tokens():
    f = FakeClient(["one", "two"])
    a, b = f.complete("sys", MSG, {}), f.complete("sys", MSG, {})
    assert (a.text, b.text) == ("one", "two") and a.usage.input_tokens > 0 and a.usage.cost_usd == 0
    assert len(f.calls) == 2 and f.calls[0]["system"] == "sys"
    with pytest.raises(LLMError):
        f.complete("sys", MSG, {})  # script exhausted


def test_fake_client_can_answer_by_function_and_simulate_a_refusal():
    f = FakeClient(lambda system, messages: None)
    assert f.complete("s", MSG, {}).refusal
