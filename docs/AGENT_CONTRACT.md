# Household agent contract (Te Tengo Captura)

> The team decided to process video on the household PC (MediaPipe on CPU), so the agent sends **events**, not video (ADR 0004; the change request to the project charter is pending). Event names and fields come from the validated classifier in `te-tengo-desktop-pywebview` (`docs/classification-spec.md`).

## Authentication
- **Installation:** the project team installs the agent with a fixed configuration (household, webcam and room) and an installation credential.
- **Registration:** at startup the agent registers its camera and receives a **per-camera JWT** with the claims `hogar_id`, `camara_id` and `rol = AGENTE`. The token only works for that household (see `MULTITENANCY.md`).

## Endpoints (version 1, header `Api-Version: 1`)
| Method and path | Purpose | Stories |
|---|---|---|
| `POST /api/agente/camaras/registro` | Registers the camera when the agent starts, using the installation credential, and returns the camera token | US-06 (CA-06.1) |
| `GET /api/agente/estado-captura` | Current consent and pauses: the agent does not process without consent or during a pause | US-05 (CA-05.2), US-22 |
| `POST /api/agente/senal` | Periodic heartbeat; updates the time of the last signal | US-07 |
| `POST /api/agente/eventos` | Detected event (body below); idempotent by `eventoId` | US-11 to US-21 |
| `POST /api/agente/eventos/{eventoId}/clip` | Returns a pre-signed S3 PUT URL to upload the 6 s + 6 s clip | US-18 |
| `GET /api/agente/configuracion` | Current classification thresholds and agent version, so agents can update themselves | — |

## Detected event
```json
{
  "eventoId": "0192f6e4-...",
  "tipo": "caida",
  "ocurridoEn": "2026-10-07T15:04:31.250Z",
  "parametros": { "angulo_grados": 22.1, "razon_ancho_alto": 1.8, "velocidad": 0.41 }
}
```
`tipo` is one of:
- `caida`
- `caida_confirmada` (30 s on the floor)
- `movimiento_inestable`
- `recuperacion`
- `deteccion_no_confiable` (5 min without seeing the person)

**Backend rules:**
- **Disconnection:** if no heartbeat arrives in time, the camera becomes `DESCONECTADA` and push `CAMARA_DESCONECTADA` is sent (CA-07.2). The heartbeat timeout **[implementation choice]** is 3 missed heartbeats, with a heartbeat every 30 s.
- **Latency:** a fall must reach the family as a push **in less than 10 s** (CA-11.3, CA-16.1).

## Request and response bodies
> **[implementation choice]** The backlog fixes what each endpoint does, not its JSON. These shapes are shared by `te-tengo-general-api` and `te-tengo-desktop-pywebview`; change them in both repositories at once. JSON fields are camelCase, times are ISO-8601 UTC, errors are RFC 9457 `ProblemDetail` with `codigo`.

**Registration** — `POST /api/agente/camaras/registro` (no bearer token)
```json
{ "credencialInstalacion": "…", "nombreHabitacion": "Sala", "versionAgente": "1.0.0" }
```
→ `200 {camaraId, hogarId, token, expiraEn, nombreHabitacion}`. Registering again with the same credential returns the same `camaraId`, a new token, and the room name stored in the backend (the app can rename it, CA-06.2). Errors: `401 CREDENCIAL_INVALIDA`.

**Capture state** — `GET /api/agente/estado-captura`, and also the response of every heartbeat
```json
{ "capturaPermitida": false, "motivo": "EN_PAUSA", "pausadaHasta": "2026-10-07T20:00:00Z", "nombreHabitacion": "Sala" }
```
`motivo` is `SIN_CONSENTIMIENTO`, `EN_PAUSA` or `null` (allowed). The agent does not capture nor classify while `capturaPermitida` is `false` (CA-05.2, CA-22.1) and resumes on its own when it turns `true` (CA-22.3).

**Heartbeat** — `POST /api/agente/senal` every 30 s
```json
{ "webcamConectada": true, "deteccionConfiable": true, "versionAgente": "1.0.0" }
```
→ `200 EstadoCaptura` (the body above). With `webcamConectada: false` the backend treats the camera as disconnected right away (CA-07.2), without waiting for missed heartbeats.

**Event** — `POST /api/agente/eventos` with the body in "Detected event" → `202 {eventoId, alertaId | null}`. A repeated `eventoId` returns `200` with the same body and creates nothing (the agent retries after network errors). Errors: `409 CAPTURA_NO_PERMITIDA` if consent is missing or the camera is paused.

**Clip upload** — `POST /api/agente/eventos/{eventoId}/clip`
```json
{ "contentType": "video/mp4", "tamanoBytes": 734003 }
```
→ `201 {urlSubida, cabeceras: {nombre: valor}, expiraEn}`. The agent then sends `PUT urlSubida` with those headers and the MP4 body. Errors: `404 EVENTO_NO_ENCONTRADO`.

**Configuration** — `GET /api/agente/configuracion` → `200 {versionAgente, umbrales: {…}}`, where `umbrales` uses the field names of `Umbrales` in the detection package (`docs/classification-spec.md`); unknown or missing fields keep the agent's local values.

**Token expiry:** any `401` other than `CREDENCIAL_INVALIDA` makes the agent register again with its installation credential.

**Live view (pending):** how the agent learns about a live-view request and where it sends the stream depends on the transport decision recorded in `docs/BLOCKERS.md`.
