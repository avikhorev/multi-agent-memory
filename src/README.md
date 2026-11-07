# src

## Overview

Source root of the project (`pyproject.toml` sets `where = ["src"]` for package discovery and `pythonpath = ["src"]` for pytest). It contains a single package, `mam`, and no source files of its own.

## Subdirectories & Boundaries

- mam: [./mam/README.md](./mam/README.md) - memory systems for a multi-agent project and the benchmark that evaluates them: scenario generator and validator, scoring, extractors, model agents, and the evaluation runners; the memory systems themselves are in [./mam/systems/README.md](./mam/systems/README.md).
