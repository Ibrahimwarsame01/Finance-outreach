"""Ensures the repo root is importable so tests can `from src import ...`.

pytest adds the directory containing this conftest.py to sys.path, which makes
the `src` package importable regardless of where pytest is invoked from.
"""
