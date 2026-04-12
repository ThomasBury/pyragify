# Repository Guidelines

## Project Structure & Module Organization
Core code lives in `src/pyragify/`: `cli.py` exposes the Typer CLI, `processor.py` handles chunking, `graph.py` builds/query relationships, and `utils.py` holds shared helpers. Tests are in `tests/`, currently centered on processor behavior in `tests/test_processor.py`. Documentation is under `docs/`, with API reference pages generated via `scripts/gen_ref_pages.py` and navigation configured in `mkdocs.yml`. Use `config.yaml` as the local entry point for repository-processing settings; treat generated `output/` and `graphs/` artifacts as disposable.

## Build, Test, and Development Commands
Use `uv` for local development because the repository includes `uv.lock`.

- `uv sync --group dev --group docs` installs runtime, test, and docs dependencies.
- `uv run pytest` runs the full test suite.
- `uv run pytest tests/test_processor.py -k markdown` runs a focused test slice while iterating.
- `uv run mkdocs serve` starts the local documentation site.
- `uv run mkdocs build` verifies the docs and generated reference pages build cleanly.
- `uv run pyragify process-repo --config-file config.yaml` exercises the CLI against the sample config.

## Coding Style & Naming Conventions
Target Python 3.9+ and follow existing PEP 8 style with 4-space indentation. Prefer `snake_case` for modules, functions, and variables, and `PascalCase` for classes. Keep type hints on public functions and use short NumPy-style docstrings where the module already does. Typer command functions are written in `snake_case` and exposed as hyphenated CLI commands, for example `process_repo` -> `process-repo`.

## Testing Guidelines
Tests use `pytest` with temporary-path fixtures and parametrization. Name files `test_*.py` and test functions `test_*`. Add regression coverage for new file handlers, CLI option routing, and graph behavior; no coverage threshold is configured, so rely on focused tests for every new branch or bug fix.

## Commit & Pull Request Guidelines
Recent history follows Conventional Commit prefixes with emoji shortcodes, for example `feat: :sparkles: add support for other languages` and `test: :test_tube: add test suite`. Keep commits scoped and imperative. Pull requests should explain the behavior change, link related issues, list the commands you ran (`uv run pytest`, `uv run mkdocs build`), and include sample CLI output or docs screenshots when user-facing behavior changes.
