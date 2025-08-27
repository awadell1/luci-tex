# Repository Guidelines

## Project Structure & Modules
- `src/luci/`: CLI and commands (`cli.py`, `__main__.py`).
- `tests/`: Pytest suite (`test_*.py`) with shared fixtures in `conftest.py` and `utils.py`.
- `docs/`: Sphinx sources and CLI docs; built HTML is written to `build/html/` when using autobuild.
- `build/`, `dist/`: Local build artifacts. Do not commit.

## Build, Test, and Development
- Install dev deps: `uv pip install -e .[dev,docs]`
- Run CLI locally: `uv run luci --help` or `uv run python -m luci check`.
- Lint and format: `uv run ruff check --fix .` and `uv run ruff format .`
- Run tests: `uv run pytest -q`
- Pre-commit (recommended): `uv run pre-commit run -a`
- Build docs (live): `uv run --group docs sphinx-autobuild docs build/html`

## Coding Style & Naming
- Python 3.10+, 4-space indent, type hints required in new/modified code.
- Use Ruff for linting/formatting (configured via `.pre-commit-config.yaml`).
- Naming: modules and functions `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE`.
- CLI: register commands in `src/luci/cli.py` via `cli.command()(your_func)` and prefer clear, action-oriented names (e.g., `merge-bibs`).

## Testing Guidelines
- Framework: pytest. Place tests under `tests/` as `test_<feature>.py`.
- Keep tests fast and deterministic; avoid network and external tools unless explicitly mocked.
- Run a focused file: `uv run pytest tests/test_check.py -q`.
- Add tests alongside changes; cover edge cases (e.g., missing files, undefined refs, duplicate keys).
- When replicating issues, generate the LaTeX source code to reproduce the issue (not the output log files)

## Commit & Pull Request Guidelines
- Commit style mirrors history: `ci:`, `test:`, `chore:`, `docs:`, `fix:`/`bug:`, `archive:`.
  Example: `fix: handle inline includes in archive`.
- Write imperative, concise subjects; wrap body at ~72 chars when needed.
- PRs should include: clear description, rationale, before/after examples (e.g., CLI command and output), tests updated/added, and any docs updates.
- Link issues using GitHub keywords (e.g., `Closes #123`).

## Changelog
- Location: `CHANGELOG.md`, using Keep a Changelog and SemVer.
- Add entries under `## [Unreleased]`, grouped by sections like `Added`, `Changed`, `Fixed`, `Removed`, or `Tests` (match current file).
- Entry style: concise and scoped. Example: `archive: Resolve .cls vs .bst ambiguity`.
- On release: create `## [x.y.z] - YYYY-MM-DD`, move Unreleased items, update link refs at the bottom, and tag `vX.Y.Z`.
- Do not rewrite past versions; add follow-ups in a new version.

## Security & Configuration Tips
- Some features rely on external tools: `bibtex-tidy` (dedupe) and `tectonic` (archive validation). Install as needed or gate usage in tests.
- Use `luci check --json` for CI-friendly output and strict mode for gating: `uv run luci check --strict --json`.
