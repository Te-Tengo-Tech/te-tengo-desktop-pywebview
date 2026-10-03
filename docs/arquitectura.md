# Arquitectura interna

## Principios

1. **Los mismos nombres que la arquitectura del sistema.** Cada carpeta de `src/detection_worker/` corresponde a un componente de la arquitectura lógica (ver la tabla del [README](../README.md)).
2. **Organización por dominio, no por tipo de archivo.** Cada módulo agrupa su `router.py`, `service.py`, `schemas.py`, etc. Es la estructura que recomienda *FastAPI Best Practices* (Zhanymkanov, s.f.), inspirada en *Dispatch* de Netflix. La división en routers sigue la guía oficial *Bigger Applications* (FastAPI, s.f.).
3. **Núcleo puro y adaptadores** (arquitectura hexagonal, Cockburn, 2005):
   - `clasificacion/` no importa nada de red, cámara ni AWS: recibe poses y devuelve eventos, y se prueba con secuencias sintéticas o grabadas.
   - Lo externo entra por **puertos** (`typing.Protocol`): `EstimadorPose`, `PublicadorEventos` y `AlmacenClips`. En las pruebas, esos puertos se reemplazan por dobles.
4. **La CPU, en otro proceso.** MediaPipe corre en un `ProcessPoolExecutor`, porque esperar una tarea de CPU dentro de una ruta `async`, o mandarla a un hilo, no ayuda por el GIL (Zhanymkanov, s.f.). Ver [ADR 0003](adr/0003-mediapipe-en-proceso-aparte.md).
5. **Disposición `src/`** (PyPA, s.f.): las pruebas usan el paquete instalado y no los archivos sueltos.

## Módulos

```
src/detection_worker/
├── main.py              create_app(): arma FastAPI, monta routers y adaptadores (lifespan)
├── config.py            Settings (pydantic-settings, prefijo TT_)
├── ingesta/
│   ├── router.py        WS /v1/ingesta/{camara_id}: autenticación y bucle de recepción
│   ├── protocolo.py     formato binario [instante][JPEG]
│   ├── buffer.py        búfer del clip: 6 s antes y 6 s después
│   └── service.py       ProcesadorCamara: orquesta pose → clasificación → eventos → clips
├── pose/
│   ├── schemas.py       Landmark, Pose, índices de MediaPipe
│   └── service.py       puerto EstimadorPose + MediaPipeEstimador (proceso aparte)
├── clasificacion/       NÚCLEO PURO
│   ├── parametros.py    fórmulas de Chen et al. (2020)
│   ├── umbrales.py      valores configurables con su fuente
│   └── estados.py       máquina de estados y eventos
├── eventos/
│   ├── schemas.py       EventoDetectado (contrato con el Backend API)
│   └── client.py        puerto PublicadorEventos + BackendPublicador (httpx)
├── clips/
│   └── service.py       puerto AlmacenClips + S3AlmacenClips (FFmpeg + boto3)
└── salud/router.py      GET /health
```

## Flujo de un fotograma

1. `ingesta/router.py` recibe el mensaje binario y se lo entrega al `ProcesadorCamara` de esa conexión.
2. `protocolo.decodificar` separa el instante y el JPEG, y el búfer del clip guarda el fotograma.
3. `MediaPipeEstimador.estimar` devuelve una `Pose`, o `None` si no hay nadie visible.
4. `ClasificadorCinematico.actualizar` calcula M₁, M₂ y M₃, actualiza la fase y devuelve los eventos.
5. Cada evento se publica en el Backend API. Si es una caída o un movimiento inestable, se marca para armar su clip.
6. Cuando pasan 6 s, el clip se codifica en MP4, se sube cifrado al almacenamiento y su clave se asocia al evento.

## Pendiente

| Tema | Detalle |
|---|---|
| Control de calidad y detección de movimiento | Definir criterios con fuente antes de fijar umbrales |
| Contrapresión | Descartar fotogramas atrasados si la inferencia no da abasto, para cumplir la alerta en menos de 10 s |
| Vista en vivo | Reenviar el video al Servicio de transmisión en vivo (WebSocket o MediaMTX, por decidir) |
| Contrato con el Backend API | Acordar las rutas `/internal/v1/eventos` con `te-tengo-general-api` |

## Referencias

Cockburn, A. (2005). *Hexagonal architecture*. https://alistair.cockburn.us/hexagonal-architecture/

FastAPI. (s.f.). *Bigger applications – Multiple files*. https://fastapi.tiangolo.com/tutorial/bigger-applications/

Python Packaging Authority. (s.f.). *src layout vs flat layout*. https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/

Zhanymkanov, Y. (s.f.). *FastAPI best practices*. GitHub. https://github.com/zhanymkanov/fastapi-best-practices
