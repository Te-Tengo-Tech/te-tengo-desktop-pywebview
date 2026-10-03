# Registro de cambios

Formato basado en [Keep a Changelog 1.1.0](https://keepachangelog.com/es-ES/1.1.0/); el proyecto usa [versionado semántico](https://semver.org/lang/es/).

## [Sin publicar]

### Pendiente
- Calibrar `velocidad_descenso_min` con pruebas.
- Validar la regla de movimiento inestable (búsqueda de fuentes en curso).
- Control de calidad de fotogramas, detección de movimiento y contrapresión.
- Reenvío del video al Servicio de transmisión en vivo.

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
