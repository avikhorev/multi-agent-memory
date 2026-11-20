"""Access check before a long run: one tiny call and a clear message if it failed.

Why: a long run over hundreds of scenarios must not fail an hour in because of a
missing key or a wrong CLI version. Better to find out in seconds.

  python -m mam.preflight
"""
from __future__ import annotations

import sys

from mam.llm import PINNED_CLI_VERSION, ClaudeCliClient, InfrastructureError, LLMError

# Exit code EX_CONFIG from sysexits.h: "no access, configuration needed".
EXIT_NO_ACCESS = 78

# Message (in English: it is shown in the console and may end up in CI logs).
NO_ACCESS = (
    "No working access to the model. Do one of the following and run the command again:\n"
    "  - pay by API key: set ANTHROPIC_API_KEY;\n"
    "  - pay by subscription: run `claude setup-token` once and set CLAUDE_CODE_OAUTH_TOKEN to the token it prints,\n"
    "    or log in once by running `claude` (not possible inside a container without a token).\n"
    "The values are passed to the model process unchanged and are never printed or stored.")
NO_CLI = (f"The `claude` command was not found or has the wrong version. Install the pinned one: "
          f"npm install -g @anthropic-ai/claude-code@{PINNED_CLI_VERSION}")

def check_access(client=None, factory=ClaudeCliClient) -> str | None:
    """None if the test call succeeded; otherwise the text of the message to show.

    factory — the client factory; in tests a stub is substituted so as not to go to the network.
    """
    try:
        client = client or factory()
        client.complete("You are a test endpoint.", [{"role": "user", "content": "Reply with exactly: OK"}], {})
    except (FileNotFoundError, InfrastructureError) as err:
        # The `claude` program itself is missing or broken — this is an installation problem.
        return f"{NO_CLI}\n({str(err)[:120]})"
    except LLMError as err:
        # The program started, but the model refused — this is an access/key problem.
        return f"{NO_ACCESS}\n(model said: {str(err)[:120]})"
    return None

def main(factory=ClaudeCliClient) -> int:
    message = check_access(factory=factory)
    if message:
        print(message, file=sys.stderr)
        return EXIT_NO_ACCESS
    print("access ok")
    return 0

if __name__ == "__main__":
    sys.exit(main())
