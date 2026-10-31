# One image for the tests, the reproduction of the tables and the live layer.
# Python 3.11 is the lowest supported version; Node and the pinned Claude Code are needed only for the live layer.
FROM node:22-slim AS node

FROM python:3.11-slim
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && npm install -g @anthropic-ai/claude-code@2.1.316 \
 && apt-get update && apt-get install -y --no-install-recommends make \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml Makefile LICENSE ./
COPY src ./src
RUN python -m venv .venv && .venv/bin/pip install --no-cache-dir -e '.[dev]'
COPY tests ./tests
COPY docs ./docs
COPY data ./data
COPY holdout ./holdout
COPY results ./results

# the pinned CLI must not update itself; credentials are given at run time (-e ANTHROPIC_API_KEY, -e CLAUDE_CODE_OAUTH_TOKEN)
ENV DISABLE_AUTOUPDATER=1
CMD ["make", "test"]
