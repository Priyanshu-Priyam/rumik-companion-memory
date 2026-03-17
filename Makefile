PYTHON ?= python3.9
PIP ?= $(PYTHON) -m pip

.PHONY: install run-app run-evals-baseline run-evals-improved test

install:
	$(PIP) install -r requirements.txt

run-app:
	$(PYTHON) -m streamlit run app/streamlit_app.py

run-evals-baseline:
	$(PYTHON) -m evals.run_evals --brain baseline --output results/baseline.json

run-evals-improved:
	$(PYTHON) -m evals.run_evals --brain improved --output results/improved.json

test:
	$(PYTHON) -m pytest tests/ -v
