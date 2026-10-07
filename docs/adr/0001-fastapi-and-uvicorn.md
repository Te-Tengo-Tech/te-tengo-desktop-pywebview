# 0001. FastAPI and Uvicorn for the service

**Status:** accepted (2026-10-03)

## Context
The detection module is written in Python, because MediaPipe and OpenCV are Python libraries, and it must expose a WebSocket for the video and a health endpoint. The system's Backend API is separate, in Spring Boot.

## Decision
Use **FastAPI** with the **Uvicorn** ASGI server. Endpoints are split into one `APIRouter` per module, as the *Bigger Applications* guide recommends (FastAPI, s.f.).

## Consequences
- Native WebSocket support and validation with Pydantic.
- CPU tasks cannot run inside `async` routes (see ADR 0003).

FastAPI. (s.f.). *Bigger applications – Multiple files*. https://fastapi.tiangolo.com/tutorial/bigger-applications/
