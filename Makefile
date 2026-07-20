PY := .venv/bin/python

.PHONY: data ndvi quality summary e2e lint serve all

data:
	$(PY) pipeline/fetch_golf.py
	$(PY) pipeline/curate_datacenters.py
	$(PY) pipeline/fetch_context.py

ndvi:
	PYTHONUNBUFFERED=1 $(PY) pipeline/ndvi_anomaly.py

summary:
	$(PY) pipeline/build_summary.py

quality:
	PYTHONUNBUFFERED=1 $(PY) pipeline/ndvi_quality.py

e2e:
	$(PY) tests/e2e_checks.py
	$(PY) tests/claims_verify.py

lint:
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .

serve:
	$(PY) -m http.server 8737 -d site

all: data ndvi quality summary e2e
