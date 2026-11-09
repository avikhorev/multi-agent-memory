"""Проверка доступа перед долгим прогоном: один крошечный вызов и понятное сообщение, если он не удался.

Зачем: долгий прогон на сотнях сценариев не должен падать через час из-за
отсутствующего ключа или неверной версии CLI. Лучше узнать это за секунды.

  python -m mam.preflight
"""
from __future__ import annotations

import sys

from mam.llm import PINNED_CLI_VERSION, ClaudeCliClient, InfrastructureError, LLMError

# Код выхода EX_CONFIG из sysexits.h: «доступа нет, нужна настройка».
EXIT_NO_ACCESS = 78

# Сообщение (на английском: оно показывается в консоли и может уйти в CI-логи).
NO_ACCESS = (
    "No working access to the model. Do one of the following and run the command again:\n"
    "  - pay by API key: set ANTHROPIC_API_KEY;\n"
    "  - pay by subscription: run `claude setup-token` once and set CLAUDE_CODE_OAUTH_TOKEN to the token it prints,\n"
    "    or log in once by running `claude` (not possible inside a container without a token).\n"
    "The values are passed to the model process unchanged and are never printed or stored.")
NO_CLI = (f"The `claude` command was not found or has the wrong version. Install the pinned one: "
          f"npm install -g @anthropic-ai/claude-code@{PINNED_CLI_VERSION}")

def check_access(client=None, factory=ClaudeCliClient) -> str | None:
    """None, если тестовый вызов прошёл; иначе текст сообщения для показа.

    factory — фабрика клиента; в тестах подставляется заглушка, чтобы не ходить в сеть.
    """
    try:
        client = client or factory()
        client.complete("You are a test endpoint.", [{"role": "user", "content": "Reply with exactly: OK"}], {})
    except (FileNotFoundError, InfrastructureError) as err:
        # Нет самой программы `claude` или она сломана — это проблема установки.
        return f"{NO_CLI}\n({str(err)[:120]})"
    except LLMError as err:
        # Программа запустилась, но модель отказала — это проблема доступа/ключа.
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
