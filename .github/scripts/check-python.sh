#!/usr/bin/env bash
set -euo pipefail
uv sync --project backend --frozen --all-extras
uv lock --project backend --check
uv run --project backend --frozen ruff check backend dev_cli .github/scripts
uv run --project backend --frozen ruff format --check backend dev_cli .github/scripts
(cd backend && uv run --frozen basedpyright)
uv run --project backend --frozen basedpyright --project dev_cli/pyproject.toml
(cd backend && uv run --frozen pytest -n 4)
backend/.venv/bin/pytest -q dev_cli/tests
build_dir=$(mktemp -d "${RUNNER_TEMP:-/tmp}/zondarr-dist.XXXXXX")
trap 'rm -rf "$build_dir"' EXIT
uv build --project backend --no-sources --out-dir "$build_dir"
