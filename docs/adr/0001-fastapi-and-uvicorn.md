# 0001. FastAPI y Uvicorn para el servicio

**Estado:** aceptada (2026-10-03)

## Contexto
El módulo de detección es Python, porque MediaPipe y OpenCV son librerías de Python, y debe exponer un WebSocket para el video y un endpoint de salud. El Backend API del sistema va aparte, en Spring Boot.

## Decisión
Usar **FastAPI** con el servidor ASGI **Uvicorn**. Los endpoints se separan en un `APIRouter` por módulo, como indica la guía *Bigger Applications* (FastAPI, s.f.).

## Consecuencias
- WebSocket nativo y validación con Pydantic.
- Las tareas de CPU no pueden ir dentro de rutas `async` (ver ADR 0003).

FastAPI. (s.f.). *Bigger applications – Multiple files*. https://fastapi.tiangolo.com/tutorial/bigger-applications/
