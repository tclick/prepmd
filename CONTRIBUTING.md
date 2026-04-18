# Contributing

1. Create a branch from `main`.
2. Run linting and tests locally.
3. Submit a pull request with a clear summary.

## Golden integration tests

Golden snapshots for deterministic `prepmd setup` integration tests are stored under
`/home/runner/work/prepmd/prepmd/tests/golden/`.

- Run golden tests: `python -m pytest -q tests/test_golden_setup.py`
- Intentionally update snapshots: `UPDATE_GOLDEN=1 python -m pytest -q tests/test_golden_setup.py`

The golden helper normalizes line endings and path separators, and compares:

- a sorted, normalized project tree listing (`tree.txt`)
- deterministic text outputs under `files/`
