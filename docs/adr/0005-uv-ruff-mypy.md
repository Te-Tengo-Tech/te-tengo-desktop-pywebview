# 0005. uv, Ruff and mypy as the project tools

**Status:** accepted (2026-10-03)

## Context
A reproducible environment and uniform code quality are needed between the two authors and in CI.

## Decision
- **uv:** manages Python, the dependencies and `uv.lock`, which is versioned.
- **Ruff:** linting and formatting.
- **mypy** in strict mode.
- **pytest** with coverage.
- **pre-commit:** runs Ruff and validates Conventional Commits before each commit.
- **GitHub Actions** runs everything again on each *pull request*.

## Consequences
- `make revisar` and `make probar` give the same result locally and in CI.
- The Dockerfile uses the official uv image with the multi-stage pattern (Astral, s.f.).

Astral. (s.f.). *Using uv in Docker*. https://docs.astral.sh/uv/guides/integration/docker/
