PY ?= .venv/bin/python

.PHONY: venv test

venv:
	python3 -m venv .venv
	.venv/bin/pip install -e '.[dev]'

test:
	$(PY) -m pytest

.PHONY: dataset test-generator

dataset:
	PYTHONPATH=src $(PY) -m mam.generate --split dev --out data/dev
	PYTHONPATH=src $(PY) -m mam.generate --split eval --out data/eval
	PYTHONPATH=src $(PY) -m mam.generate --split holdout --out holdout

test-generator:
	$(PY) -m pytest tests/acceptance -m "not memory"
