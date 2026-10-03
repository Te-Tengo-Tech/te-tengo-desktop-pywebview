# te-tengo-service-detection-worker

**Módulo de detección** de Te Tengo, el sistema basado en estimación de pose para la detección de caídas en adultos mayores en su vivienda.

Recibe el video del Agente de captura, estima la pose de la persona con MediaPipe y clasifica el movimiento con **umbrales cinemáticos, sin entrenar modelos**. Detecta caídas, caídas confirmadas, recuperaciones, movimientos inestables y periodos de detección no confiable. Reporta cada evento al Backend API del sistema y guarda el clip de 6 s antes y 6 s después del evento.

## Lugar en la arquitectura

Este repositorio implementa el contenedor **Módulo de detección** del modelo C4. Corresponde a la **Capa de Procesamiento de Video** de la arquitectura lógica, salvo el Servicio de transmisión en vivo, que va aparte.

| Componente de la arquitectura lógica | Carpeta |
|---|---|
| Servicio de ingesta de video | [`src/detection_worker/ingesta/`](src/detection_worker/ingesta) |
| Servicio de estimación de pose | [`src/detection_worker/pose/`](src/detection_worker/pose) |
| Servicio de clasificación cinemática | [`src/detection_worker/clasificacion/`](src/detection_worker/clasificacion) |
| Comunicación con el Backend API del sistema | [`src/detection_worker/eventos/`](src/detection_worker/eventos) |
| Persistencia de clips de video (escritura) | [`src/detection_worker/clips/`](src/detection_worker/clips) |

```
Agente de captura ──WSS (JPEG 480p, 5-10 fps)──► ingesta ──► pose (MediaPipe, proceso aparte)
                                                    │                │ 33 landmarks
                                                    │                ▼
                                                    │          clasificacion ──eventos──► Backend API
                                                    └──clip 6 s + 6 s──► clips ──► almacenamiento de objetos
```

La organización interna se explica en [docs/arquitectura.md](docs/arquitectura.md). Las fórmulas y su origen están en [docs/especificacion-clasificacion.md](docs/especificacion-clasificacion.md).

## Requisitos

| Herramienta | Versión |
|---|---|
| Python | 3.11 (lo exige `mediapipe==0.10.35`, ver [ADR 0003](docs/adr/0003-mediapipe-en-proceso-aparte.md)) |
| [uv](https://docs.astral.sh/uv/) | 0.12 o superior |
| FFmpeg | Cualquiera reciente (arma los clips MP4) |
| Docker | 29 o superior (opcional, para la imagen) |

## Puesta en marcha

```bash
make instalar      # crea .venv con uv e instala los hooks de pre-commit
make modelo        # descarga pose_landmarker_lite.task en models/
make env          # crea .env con tokens locales (no sobrescribe uno existente)
make ejecutar      # http://localhost:8001/docs
```

## Comandos

| Comando | Qué hace |
|---|---|
| `make instalar` | Instala las dependencias (`uv sync`) y los hooks de pre-commit |
| `make env` | Crea `.env` desde `.env.example` con tokens locales aleatorios |
| `make modelo` | Descarga el modelo de MediaPipe |
| `make ejecutar` | Levanta el servicio con recarga automática |
| `make formatear` | Formatea el código con Ruff |
| `make revisar` | Lint (Ruff), formato y tipos (mypy en modo estricto) |
| `make probar` | Pruebas con cobertura (pytest) |
| `make imagen` | Construye la imagen Docker |

## Interfaces

| Interfaz | Detalle |
|---|---|
| `GET /health` | Liveness para Docker y el proxy inverso |
| `WS /v1/ingesta/{camara_id}` | Video del Agente de captura. Formato en [docs/protocolo-ingesta.md](docs/protocolo-ingesta.md). |
| Backend API → `POST /internal/v1/eventos` | Eventos detectados (contrato provisional) |
| Backend API → `PUT /internal/v1/eventos/{id}/clip` | Clave del clip guardado |

## Configuración

Todas las variables llevan el prefijo `TT_`. La lista completa está en [.env.example](.env.example).

`TT_CLASIFICACION__VELOCIDAD_DESCENSO_MIN` **no tiene valor por defecto**: debe calibrarse con pruebas (regla R1 de la especificación). Mientras esté vacío, el servicio arranca (`/health`, `/docs`), pero la ingesta cierra el WebSocket con el código 1011.

## Estado

Versión inicial (0.1.0). Pendiente:
- Calibrar el umbral de velocidad.
- Validar la regla de movimiento inestable.
- Detección de movimiento y control de calidad de fotogramas.
- Descartar fotogramas atrasados (contrapresión).
- Reenviar el video al Servicio de transmisión en vivo.

El detalle está en [CHANGELOG.md](CHANGELOG.md).

## Contribuir

Consulta [CONTRIBUTING.md](CONTRIBUTING.md): Conventional Commits, ramas y revisión antes de integrar.

---

Proyecto de tesis, Ingeniería de Software, Universidad Peruana de Ciencias Aplicadas (UPC). Autores: Jhosepmyr Gutierrez Soto y Elmer Riva Rodriguez.
