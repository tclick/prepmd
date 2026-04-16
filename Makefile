.PHONY: test lint typecheck format

test:
python -m pytest

lint:
ruff check .

typecheck:
basedpyright

format:
ruff format .
