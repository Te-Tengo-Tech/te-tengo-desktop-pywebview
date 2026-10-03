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
| `make camara` | Prueba el clasificador con la webcam o un video, con dibujo en pantalla |
| `make agente` | Envía la webcam o un video al worker como el agente real |
| `make datasets` | Descarga URFD y CAUCAFall |
| `make validar` | Valida el clasificador con los datasets y genera el reporte |
| `make formatear` | Formatea el código con Ruff |
| `make revisar` | Lint (Ruff), formato y tipos (mypy en modo estricto) |
| `make probar` | Pruebas con cobertura (pytest) |
| `make imagen` | Construye la imagen Docker |

## Probar con la cámara o con videos

Hay dos herramientas en `scripts/`. Ninguna necesita el backend ni el agente real.

**1. Prueba local del clasificador** (`make camara`). Abre la webcam o un video y usa el mismo código del worker. Dibuja el esqueleto, la línea central (cian), el rectángulo del cuerpo (amarillo), el ángulo, la razón, la velocidad, la fase y los eventos.

```bash
make camara                                          # webcam: solo mide (sin umbral no clasifica)
make camara ARGS="--velocidad-min 0.01"              # clasifica con el umbral calibrado
make camara ARGS="--video fall-01-cam0.mp4 --recorte 320,0,320,240 --csv mediciones.csv"
```

- **Videos de URFD:** traen la profundidad a la izquierda y el RGB a la derecha. Usa `--recorte 320,0,320,240`.
- **`--csv`:** guarda el ángulo, la razón y la velocidad de cada fotograma; sirve para calibrar.
- **`--sin-ventana`:** solo imprime los eventos, sin abrir ventana.
- **En macOS:** la primera vez hay que dar permiso de cámara a la terminal o al IDE (Ajustes del Sistema → Privacidad y seguridad → Cámara).
- **iPhone como cámara (Cámara de Continuidad):** con iOS 16 o superior, macOS Ventura o superior y la misma cuenta de Apple, el iPhone aparece como una cámara más. Para ver su índice: `make camara ARGS="--listar-camaras"`; después úsalo con `--camara N`. Evita la «Desk View», que muestra el escritorio desde arriba.

**2. Agente simulado** (`make agente`). Envía la webcam o un video al worker por WebSocket, igual que lo hará Te Tengo Captura (480p, 8 fps y JPEG). Prueba el servicio completo:

```bash
make ejecutar                                    # en una terminal (requiere el umbral en .env)
make agente                                      # en otra: webcam
make agente ARGS="--video fall-01-cam0.mp4 --recorte 320,0,320,240"
```

El worker registra cada evento en su log (`Evento detectado: caida en camara-local …`). Sin backend ni SeaweedFS, también registra un aviso de que no pudo publicarlo, pero sigue funcionando.

## Validación con datasets públicos

El clasificador se validó con **URFD** (70 videos) y **CAUCAFall** (100 videos) en las condiciones de producción: 480p, 8 fps, JPEG y MediaPipe en modo VIDEO. Para medir sin sesgo se dejó fuera cada grupo al calibrar:

| Sensibilidad | Especificidad | Exactitud | Recuperaciones falsas |
|---|---|---|---|
| **81,2 %** | **81,1 %** | **81,2 %** | 0 de 30 |

Protocolo, resultados por actividad, cambios hechos y límites: [docs/validacion.md](docs/validacion.md). Para reproducirlo:

```bash
make datasets   # descarga los datasets en datos/ (no se versionan)
make validar    # genera resultados/reporte.md
```

## Interfaces

| Interfaz | Detalle |
|---|---|
| `GET /health` | Liveness para Docker y el proxy inverso |
| `WS /v1/ingesta/{camara_id}` | Video del Agente de captura. Formato en [docs/protocolo-ingesta.md](docs/protocolo-ingesta.md). |
| Backend API → `POST /internal/v1/eventos` | Eventos detectados (contrato provisional) |
| Backend API → `PUT /internal/v1/eventos/{id}/clip` | Clave del clip guardado |

## Configuración

Todas las variables llevan el prefijo `TT_`. La lista completa está en [.env.example](.env.example).

`TT_CLASIFICACION__VELOCIDAD_DESCENSO_MIN` no tiene valor por defecto en el código; `.env.example` trae el valor calibrado (0,01; ver [docs/validacion.md](docs/validacion.md)). Mientras esté vacío, el servicio arranca (`/health`, `/docs`), pero la ingesta cierra el WebSocket con el código 1011.

## Estado

Versión 0.2.0: clasificador validado con URFD y CAUCAFall. Pendiente:
- Validar la regla de movimiento inestable con grabaciones propias (los datasets no tienen tambaleos etiquetados).
- Detección de movimiento y control de calidad de fotogramas.
- Descartar fotogramas atrasados (contrapresión).
- Reenviar el video al Servicio de transmisión en vivo.

El detalle está en [CHANGELOG.md](CHANGELOG.md).

## Contribuir

Consulta [CONTRIBUTING.md](CONTRIBUTING.md): Conventional Commits, ramas y revisión antes de integrar.

---

Proyecto de tesis, Ingeniería de Software, Universidad Peruana de Ciencias Aplicadas (UPC). Autores: Jhosepmyr Gutierrez Soto y Elmer Riva Rodriguez.
