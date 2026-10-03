# syntax=docker/dockerfile:1
# Imagen del Módulo de detección. Patrón multietapa recomendado por uv:
# https://docs.astral.sh/uv/guides/integration/docker/

# ---------- Etapa 1: dependencias y modelo
FROM python:3.11-slim-bookworm AS construccion
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

COPY scripts/descargar_modelo.sh scripts/
RUN ./scripts/descargar_modelo.sh models/pose_landmarker_lite.task

COPY src ./src
COPY README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# ---------- Etapa 2: ejecución
FROM python:3.11-slim-bookworm
# libgl1 y libglib2.0-0: los necesita opencv-contrib-python (dependencia de MediaPipe).
# ffmpeg: arma los clips MP4.
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 app

WORKDIR /app
COPY --from=construccion --chown=app:app /app /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER app

EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health')"

CMD ["uvicorn", "detection_worker.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8001"]
