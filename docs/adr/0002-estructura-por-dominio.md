# 0002. Estructura por dominio con núcleo puro y adaptadores

**Estado:** aceptada (2026-10-03)

## Contexto
El código debe ser entendible para el equipo y el asesor, y fácil de rastrear contra los diagramas de arquitectura.

## Decisión
- **Carpetas por dominio** con los nombres de los componentes de la arquitectura lógica (`ingesta`, `pose`, `clasificacion`), como recomienda *FastAPI Best Practices* (Zhanymkanov, s.f.).
- **`clasificacion` es un núcleo puro**, sin I/O. Lo externo (MediaPipe, Backend API, S3) entra por puertos `Protocol`, según la arquitectura hexagonal (Cockburn, 2005).
- **Disposición `src/`** (PyPA, s.f.).

## Consecuencias
- Las fórmulas se prueban sin cámara ni red, y sirven para validar con datasets.
- Hay un poco más de código para construir los adaptadores (`main.construir_componentes`).

Cockburn, A. (2005). *Hexagonal architecture*. https://alistair.cockburn.us/hexagonal-architecture/
Python Packaging Authority. (s.f.). *src layout vs flat layout*. https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/
Zhanymkanov, Y. (s.f.). *FastAPI best practices*. https://github.com/zhanymkanov/fastapi-best-practices
