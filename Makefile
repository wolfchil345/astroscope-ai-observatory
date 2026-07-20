.PHONY: install run test lint checks

install:
	python -m pip install --upgrade pip
	python -m pip install -e ".[dev]"

run:
	streamlit run app.py --server.address 0.0.0.0 --server.port 8501

test:
	python -m pytest -v

lint:
	python -m ruff check .

checks: lint test
