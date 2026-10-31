PY ?= .venv/bin/python

.PHONY: venv test

venv:
	python3 -m venv .venv
	.venv/bin/pip install -e '.[dev]'

test:
	$(PY) -m pytest

.PHONY: dataset test-generator memory-level smoke mutation

dataset:
	PYTHONPATH=src $(PY) -m mam.generate --split dev --out data/dev
	PYTHONPATH=src $(PY) -m mam.generate --split eval --out data/eval
	PYTHONPATH=src $(PY) -m mam.generate --split holdout --out holdout

test-generator:
	$(PY) -m pytest tests/acceptance -m "not memory"

# usage: make memory-level SPLIT=dev
SPLIT ?= dev
memory-level:
	PYTHONPATH=src $(PY) -m mam.memory_eval --split $(SPLIT) --out results/memory_level/$(SPLIT)
	PYTHONPATH=src $(PY) -m mam.tables results/memory_level/$(SPLIT) --title "$(SPLIT), memory level" > results/memory_level/$(SPLIT)/tables.md

smoke:
	PYTHONPATH=src $(PY) -m mam.run live --split dev --select smoke --systems ours,full_history --out results/live/smoke --max-cost-usd 3

# needs: pip install -e '.[mutation]'
mutation:
	.venv/bin/mutmut run --max-children 4
	.venv/bin/mutmut results
