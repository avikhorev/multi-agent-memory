"""The access check that runs before a long live run."""
import json

import pytest

from mam.llm import ClaudeCliClient, PINNED_CLI_VERSION
from mam.preflight import EXIT_NO_ACCESS, check_access, main


class Runner:
    def __init__(self, reply=None, error=None):
        self.reply, self.error = reply, error

    def __call__(self, cmd, env, cwd, timeout):
        if cmd[:2] == ["claude", "--version"]:
            return 0, f"{PINNED_CLI_VERSION} (Claude Code)", ""
        if self.error:
            raise self.error
        return 0, json.dumps(self.reply), ""


def client(reply=None, error=None):
    return ClaudeCliClient(runner=Runner(reply, error), environ={"PATH": "/bin"}, sleep=lambda s: None)


OK = {"is_error": False, "result": "OK", "usage": {}}
LOGGED_OUT = {"is_error": True, "result": "Authentication error: please log in", "usage": {}}


def test_a_working_client_passes():
    assert check_access(client(OK)) is None


def test_missing_credentials_give_a_clear_message_that_names_every_way_to_fix_it():
    msg = check_access(client(LOGGED_OUT))
    assert msg and "ANTHROPIC_API_KEY" in msg and "CLAUDE_CODE_OAUTH_TOKEN" in msg and "claude" in msg
    assert "Authentication error" not in msg or len(msg) < 600  # the raw error may be quoted, briefly


def test_a_missing_cli_is_reported_as_such():
    class NoCli(Runner):
        def __call__(self, cmd, env, cwd, timeout):
            raise FileNotFoundError("claude")
    with pytest.raises(Exception):
        ClaudeCliClient(runner=NoCli(), environ={}, sleep=lambda s: None)
    msg = check_access(None, factory=lambda: (_ for _ in ()).throw(FileNotFoundError("claude")))
    assert msg and "claude" in msg and "install" in msg.lower()


def test_main_exits_with_its_own_code_and_prints_the_message(capsys):
    code = main(factory=lambda: client(LOGGED_OUT))
    assert code == EXIT_NO_ACCESS and "ANTHROPIC_API_KEY" in capsys.readouterr().err
    assert main(factory=lambda: client(OK)) == 0
