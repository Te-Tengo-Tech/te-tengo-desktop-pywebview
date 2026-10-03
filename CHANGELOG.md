# Registro de cambios

Formato basado en [Keep a Changelog 1.1.0](https://keepachangelog.com/es-ES/1.1.0/); el proyecto usa [versionado semántico](https://semver.org/lang/es/).

## [Sin publicar]

### Pendiente
- Validar la regla de movimiento inestable con grabaciones propias.
- Control de calidad de fotogramas, detección de movimiento y contrapresión.
- Reenvío del video al Servicio de transmisión en vivo.

## [0.2.0] - 2026-10-03

### Agregado
- Validación con URFD y CAUCAFall (`scripts/descargar_datasets.py`, `scripts/evaluar.py`, `make datasets`, `make validar`) y reporte en `docs/validacion.md`: sensibilidad 81,2 %, especificidad 81,1 %, exactitud 81,2 %.
- Herramientas de prueba con webcam o video: `make camara` y `make agente`.
- Adaptación A7: la cabeza bajo los pies indica caída hacia la cámara.
- Adaptación A8: la recuperación exige 1 s erguido.

### Cambiado
- MediaPipe en modo VIDEO con un seguimiento por cámara (ADR 0006).
- Velocidad de bajada con signo, ventana de 1 s y solo con puntos visibles (A3, A6).
- Umbral de velocidad calibrado (0,01) en `.env.example`.

### Corregido
- Clips de webcams 16:9 con ancho impar.
- Recuperaciones falsas por errores de un solo fotograma de MediaPipe.

## [0.1.0] - 2026-10-03

### Agregado
- Estructura del proyecto por dominio (`ingesta`, `pose`, `clasificacion`, `eventos`, `clips`, `salud`).
- WebSocket de ingesta `/v1/ingesta/{camara_id}` con token y protocolo binario `[instante][JPEG]`.
- Estimación de pose con MediaPipe 0.10.35 en un proceso aparte.
- Clasificación con los umbrales de Chen et al. (2020): caída, caída confirmada (30 s), recuperación, movimiento inestable (propuesta) y detección no confiable (5 min).
- Búfer del clip de 6 s antes y 6 s después, codificación MP4 con FFmpeg y subida cifrada a S3.
- Publicación de eventos en el Backend API (contrato provisional).
- Herramientas: uv, Ruff, mypy estricto, pytest, pre-commit, Dockerfile multietapa y GitHub Actions.
- Documentación: arquitectura interna, especificación de la clasificación, protocolo de ingesta y ADR 0001–0005.
