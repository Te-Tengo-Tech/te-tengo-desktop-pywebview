# Internal architecture

## Principles

1. **The same names as the system architecture.** Each folder in `src/detection_worker/` maps to a component of the logical architecture (see the table in the [README](../README.md)).
2. **Organization by domain, not by file type.** Each module groups its `router.py`, `service.py`, `schemas.py`, etc. This is the structure recommended by *FastAPI Best Practices* (Zhanymkanov, s.f.), inspired by Netflix's *Dispatch*. The split into routers follows the official *Bigger Applications* guide (FastAPI, s.f.).
3. **Pure core and adapters** (hexagonal architecture, Cockburn, 2005):
   - `clasificacion/` imports nothing related to the network, the camera or AWS: it receives poses and returns events, and it is tested with synthetic or recorded sequences.
   - External dependencies come in through **ports** (`typing.Protocol`): `EstimadorPose`, `PublicadorEventos` and `AlmacenClips`. In tests, these ports are replaced with test doubles.
4. **CPU work in another process.** MediaPipe runs in a `ProcessPoolExecutor`, because awaiting a CPU task inside an `async` route, or sending it to a thread, does not help due to the GIL (Zhanymkanov, s.f.). See [ADR 0003](adr/0003-mediapipe-in-separate-process.md).
5. **`src/` layout** (PyPA, s.f.): tests use the installed package and not the loose files.

## Modules

```
src/detection_worker/
├── main.py              create_app(): builds FastAPI, mounts routers and adapters (lifespan)
├── config.py            Settings (pydantic-settings, prefix TT_)
├── ingesta/
│   ├── router.py        WS /v1/ingesta/{camara_id}: authentication and receive loop
│   ├── protocolo.py     binary format [instante][JPEG]
│   ├── buffer.py        clip buffer: 6 s before and 6 s after
│   └── service.py       ProcesadorCamara: orchestrates pose → classification → events → clips
├── pose/
│   ├── schemas.py       Landmark, Pose, MediaPipe indices
│   └── service.py       EstimadorPose port + MediaPipeEstimador (separate process)
├── clasificacion/       PURE CORE
│   ├── parametros.py    formulas from Chen et al. (2020)
│   ├── umbrales.py      configurable values with their source
│   └── estados.py       state machine and events
├── eventos/
│   ├── schemas.py       EventoDetectado (contract with the Backend API)
│   └── client.py        PublicadorEventos port + BackendPublicador (httpx)
├── clips/
│   └── service.py       AlmacenClips port + S3AlmacenClips (FFmpeg + boto3)
└── salud/router.py      GET /health
```

## Flow of a frame

1. `ingesta/router.py` receives the binary message and hands it to the `ProcesadorCamara` of that connection.
2. `protocolo.decodificar` separates the timestamp and the JPEG, and the clip buffer stores the frame.
3. `MediaPipeEstimador.estimar` returns a `Pose`, or `None` if nobody is visible.
4. `ClasificadorCinematico.actualizar` computes M₁, M₂ and M₃, updates the phase and returns the events.
5. Each event is published to the Backend API. If it is a fall or an unstable movement, it is marked so that its clip is built.
6. After 6 s, the clip is encoded as MP4, uploaded encrypted to storage, and its key is linked to the event.

## Pending

| Topic | Details |
|---|---|
| Quality control and motion detection | Define criteria with a source before setting thresholds |
| Backpressure | Drop late frames if inference cannot keep up, to meet the alert in under 10 s |
| Live view | Forward the video to the Live Streaming Service (WebSocket or MediaMTX, to be decided) |
| Contract with the Backend API | Agree on the `/internal/v1/eventos` routes with `te-tengo-general-api` |

## References

Cockburn, A. (2005). *Hexagonal architecture*. https://alistair.cockburn.us/hexagonal-architecture/

FastAPI. (s.f.). *Bigger applications – Multiple files*. https://fastapi.tiangolo.com/tutorial/bigger-applications/

Python Packaging Authority. (s.f.). *src layout vs flat layout*. https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/

Zhanymkanov, Y. (s.f.). *FastAPI best practices*. GitHub. https://github.com/zhanymkanov/fastapi-best-practices
