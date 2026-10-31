PY ?= .venv/bin/python

.PHONY: venv test

venv:
	python3 -m venv .venv
	.venv/bin/pip install -e '.[dev]'

test:
	$(PY) -m pytest
