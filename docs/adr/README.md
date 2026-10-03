# Registro de decisiones de arquitectura (ADR)

Cada decisión importante se registra en un archivo corto con el formato de Michael Nygard: **contexto, decisión, estado y consecuencias** (Nygard, 2011). Los ADR no se editan después de aceptados: si una decisión cambia, se escribe un ADR nuevo que reemplaza al anterior.

| N.° | Decisión | Estado |
|---|---|---|
| [0001](0001-fastapi-y-uvicorn.md) | FastAPI y Uvicorn para el servicio | Aceptada |
| [0002](0002-estructura-por-dominio.md) | Estructura por dominio con núcleo puro y adaptadores | Aceptada |
| [0003](0003-mediapipe-en-proceso-aparte.md) | MediaPipe 0.10.35 en un proceso aparte | Aceptada |
| [0004](0004-umbrales-de-chen.md) | Clasificación por umbrales de Chen et al. (2020) | Aceptada |
| [0005](0005-uv-ruff-mypy.md) | uv, Ruff y mypy como herramientas del proyecto | Aceptada |

Nygard, M. (2011, 15 de noviembre). *Documenting architecture decisions*. Cognitect. https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions
