# 0007. Procesar el video en la PC de la vivienda

**Estado:** aceptada por el equipo (2026-10-07). Requiere una solicitud de cambio al charter, que dice que el procesamiento se ejecuta en la nube.

## Contexto
- **Ancho de banda (medido):** enviar 480p a 8 fps en JPEG exige unos 2,8 Mbit/s de subida constante, unos 31 GB al día por cámara.
- **CPU (medido):** MediaPipe *lite* tarda 6,5 ms por fotograma en CPU (MacBook M5 Pro); a 8 fps sobra margen.
- **Evidencia:** en la revisión sistemática, la comparación directa entre borde y nube (Mundody y Guddeti, 2026) favorece al borde en latencia bajo congestión y en privacidad.

## Decisión
- **Este repositorio pasa a ser el agente de escritorio** (`te-tengo-desktop-pywebview`): un solo proyecto en Python, con la interfaz HTML del prototipo mostrada con pywebview.
- **La detección vive como paquete interno,** puro y probado.
- **Se retira** el servidor de ingesta (FastAPI y WebSocket).
- **El backend** recibe los eventos (contrato en `te-tengo-general-api/docs/CONTRATO_AGENTE.md`).

## Consecuencias
- El video no sale de la vivienda, salvo el clip del evento y la vista en vivo cuando el familiar la pide.
- La validación (`scripts/evaluar.py`) y la especificación siguen vigentes, porque el código de clasificación no cambia.
- Hay que medir los fps en la PC real del piloto.
- Hay que distribuir los umbrales y las actualizaciones desde el backend.

Mundody, S., & Guddeti, R. M. R. (2026). Pose-based fall detection with robust feature analysis and privacy-aware edge-fog-cloud deployment. *IEEE Access, 14*, 114183–114208. https://doi.org/10.1109/ACCESS.2026.3716718
