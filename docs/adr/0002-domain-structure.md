# 0002. Structure by domain with a pure core and adapters

**Status:** accepted (2026-10-03)

## Context
The code must be understandable for the team and the advisor, and easy to trace against the architecture diagrams.

## Decision
- **Folders by domain** named after the components of the logical architecture (`ingesta`, `pose`, `clasificacion`), as *FastAPI Best Practices* recommends (Zhanymkanov, s.f.).
- **`clasificacion` is a pure core**, without I/O. External dependencies (MediaPipe, Backend API, S3) come in through `Protocol` ports, following hexagonal architecture (Cockburn, 2005).
- **`src/` layout** (PyPA, s.f.).

## Consequences
- The formulas are tested without a camera or a network, and they can be used for validation with datasets.
- There is a bit more code to build the adapters (`main.construir_componentes`).

Cockburn, A. (2005). *Hexagonal architecture*. https://alistair.cockburn.us/hexagonal-architecture/
Python Packaging Authority. (s.f.). *src layout vs flat layout*. https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/
Zhanymkanov, Y. (s.f.). *FastAPI best practices*. https://github.com/zhanymkanov/fastapi-best-practices
