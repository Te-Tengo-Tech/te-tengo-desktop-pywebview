# 0005. uv, Ruff y mypy como herramientas del proyecto

**Estado:** aceptada (2026-10-03)

## Contexto
Se necesita un entorno reproducible y una calidad de código uniforme entre los dos autores y en CI.

## Decisión
- **uv:** gestiona Python, las dependencias y `uv.lock`, que va versionado.
- **Ruff:** lint y formato.
- **mypy** en modo estricto.
- **pytest** con cobertura.
- **pre-commit:** ejecuta Ruff y valida Conventional Commits antes de cada commit.
- **GitHub Actions** repite todo en cada *pull request*.

## Consecuencias
- `make revisar` y `make probar` dan el mismo resultado en local y en CI.
- El Dockerfile usa la imagen oficial de uv con el patrón multietapa (Astral, s.f.).

Astral. (s.f.). *Using uv in Docker*. https://docs.astral.sh/uv/guides/integration/docker/
