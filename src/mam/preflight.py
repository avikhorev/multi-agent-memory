"""Access check before a long run: one tiny call, and a clear message when it cannot be made.

  python -m mam.preflight
"""
from __future__ import annotations

import sys

from mam.llm import PINNED_CLI_VERSION, ClaudeCliClient, InfrastructureError, LLMError

EXIT_NO_ACCESS = 78

NO_ACCESS = (
    "No working access to the model. Do one of the following and run the command again:\n"
    "  - pay by API key: set ANTHROPIC_API_KEY;\n"
    "  - pay by subscription: run `claude setup-token` once and set CLAUDE_CODE_OAUTH_TOKEN to the token it prints,\n"
    "    or log in once by running `claude` (not possible inside a container without a token).\n"
    "The values are passed to the model process unchanged and are never printed or stored.")
NO_CLI = (f"The `claude` command was not found or has the wrong version. Install the pinned one: "
          f"npm install -g @anthropic-ai/claude-code@{PINNED_CLI_VERSION}")


def check_access(client=None, factory=ClaudeCliClient) -> str | None:
    """None when a test call works, otherwise the message to show."""
    try:
        client = client or factory()
        client.complete("You are a test endpoint.", [{"role": "user", "content": "Reply with exactly: OK"}], {})
    except (FileNotFoundError, InfrastructureError) as err:
        return f"{NO_CLI}\n({str(err)[:120]})"
    except LLMError as err:
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
