PY ?= .venv/bin/python
SPLIT ?= dev
SIZE ?= A
REPEATS ?= 2
WORKERS ?= 8
MAX_COST ?= 10
# new live runs go to their own directory; results/live/main holds the committed run and is only read
OUT ?= results/live/rerun
DIR ?= $(OUT)
IMAGE ?= mam

.PHONY: venv test test-generator dataset memory-level reproduce doctor live live-tables smoke \
        extraction-trial extraction mutation docs-check docker-build docker-test docker-reproduce docker-live

venv:
	python3 -m venv .venv
	.venv/bin/pip install -e '.[dev]'

test:
	$(PY) -m pytest

# stdlib only, no LLM or dependency installation: docs, frozen inputs/results and evidence
docs-check:
	python3 scripts/check_docs.py
	python3 -m unittest scripts.test_check_docs scripts.test_check_frozen_artifacts
	python3 scripts/check_frozen_artifacts.py
	python3 scripts/evidence_summary.py --verify

test-generator:
	$(PY) -m pytest tests/acceptance -m "not memory"

# regenerate the scenarios (identical to the committed files on Python 3.11 to 3.13)
dataset:
	PYTHONPATH=src $(PY) -m mam.generate --split dev --out data/dev
	PYTHONPATH=src $(PY) -m mam.generate --split eval --out data/eval
	PYTHONPATH=src $(PY) -m mam.generate --split holdout --out holdout

# memory level, no model: usage `make memory-level SPLIT=eval`. The cache variants (saved model answers) are
# added when results/extraction/$(SPLIT)/cache.jsonl exists.
memory-level:
	PYTHONPATH=src $(PY) -m mam.memory_eval --split $(SPLIT) --out results/memory_level/$(SPLIT) \
		$(if $(wildcard results/extraction/$(SPLIT)/cache.jsonl),--cache results/extraction/$(SPLIT)/cache.jsonl)
	PYTHONPATH=src $(PY) -m mam.tables results/memory_level/$(SPLIT) --title "$(SPLIT), memory level" \
		> results/memory_level/$(SPLIT)/tables.md

# no model, no network: recompute the memory level from the dataset and the saved answers, rebuild all tables
# from the saved raw results. Compare the output with the committed files (`git diff --stat results`); the files
# in results/memory_level/*/timing/ are measurements and differ from run to run.
reproduce:
	$(MAKE) memory-level SPLIT=eval
	$(MAKE) memory-level SPLIT=holdout
	@if [ -d results/live/main/units ]; then $(MAKE) live-tables DIR=results/live/main; else echo "no live results in results/live/main: NOT RUN"; fi

# tables of one live run directory: `make live-tables DIR=results/live/main` (default: OUT)
live-tables:
	PYTHONPATH=src $(PY) -m mam.live_tables $(DIR) > $(DIR)/tables.md

# checks that the model can be reached (ANTHROPIC_API_KEY, CLAUDE_CODE_OAUTH_TOKEN or a login of `claude`)
doctor:
	PYTHONPATH=src $(PY) -m mam.preflight

# live layer with real agents. SIZE is A or B, see docs/DECISIONS.md. Resumable: run it again after an interruption.
live: doctor
	PYTHONPATH=src $(PY) -m mam.run live --split eval --select $(SIZE) --repeats $(REPEATS) --workers $(WORKERS) \
		--out $(OUT) --max-cost-usd $(MAX_COST)

smoke: doctor
	PYTHONPATH=src $(PY) -m mam.run live --split dev --select smoke --systems ours,full_history --out results/live/smoke_check --max-cost-usd 3

# extraction pass: the model reads every source entry once and writes the session summaries; answers are saved
extraction-trial: doctor
	PYTHONPATH=src $(PY) -m mam.extraction run --split dev --select trial --out results/extraction/dev_trial --max-cost-usd 3
	PYTHONPATH=src $(PY) -m mam.extraction merge --in results/extraction/dev_trial --out results/extraction/dev_trial/cache.jsonl

extraction: doctor
	PYTHONPATH=src $(PY) -m mam.extraction run --split eval --out results/extraction/eval --max-cost-usd $(MAX_COST)
	PYTHONPATH=src $(PY) -m mam.extraction merge --in results/extraction/eval --out results/extraction/eval/cache.jsonl
	PYTHONPATH=src $(PY) -m mam.extraction run --split holdout --out results/extraction/holdout --max-cost-usd $(MAX_COST)
	PYTHONPATH=src $(PY) -m mam.extraction merge --in results/extraction/holdout --out results/extraction/holdout/cache.jsonl

# needs: pip install -e '.[mutation]'
mutation:
	.venv/bin/mutmut run --max-children 4
	.venv/bin/mutmut results

# the same targets inside a container; the model credentials are passed from the environment, never stored
docker-build:
	docker build -t $(IMAGE) .

docker-test: docker-build
	docker run --rm $(IMAGE) make test

docker-reproduce: docker-build
	docker run --rm -v "$(CURDIR)/results:/app/results" $(IMAGE) make reproduce

docker-live: docker-build
	docker run --rm -e ANTHROPIC_API_KEY -e CLAUDE_CODE_OAUTH_TOKEN -v "$(CURDIR)/results:/app/results" \
		$(IMAGE) make live SIZE=$(SIZE) REPEATS=$(REPEATS) WORKERS=$(WORKERS) MAX_COST=$(MAX_COST) OUT=$(OUT)
