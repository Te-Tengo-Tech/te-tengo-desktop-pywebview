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
- **Disconnection:** if no heartbeat arrives in time, or a heartbeat reports `webcamConectada: false`, the camera becomes `DESCONECTADA` and push `CAMARA_DESCONECTADA` is sent (CA-07.2). The heartbeat timeout **[implementation choice]** is 3 missed heartbeats, with a heartbeat every 30 s.
- **Latency:** a fall must reach the family as a push **in less than 10 s** (CA-11.3, CA-16.1).

## Request and response bodies
> **[implementation choice]** The backlog fixes what each endpoint does, not its JSON. These shapes are shared by `te-tengo-general-api` and `te-tengo-desktop-pywebview`; change them in both repositories at once. JSON fields are camelCase, times are ISO-8601 UTC, errors are RFC 9457 `ProblemDetail` with `codigo`.

**Registration** — `POST /api/agente/camaras/registro` (no bearer token)
```json
{ "credencialInstalacion": "…", "nombreHabitacion": "Sala", "versionAgente": "1.0.0" }
```
→ `200 {camaraId, hogarId, token, expiraEn, nombreHabitacion}`.
- The first registration creates the camera with the room name of the installation (CA-06.1). Registering again with the same credential returns the same `camaraId`, a new token, and the room name stored in the backend (the app can rename it, CA-06.2).
- `versionAgente` is optional; the backend only logs it.
- The token lasts 30 days; the agent registers again at startup or when it gets a `401` (see "Token expiry").
- The project team creates the credential with `scripts/create-installation.sh <hogar-id>` (only its SHA-256 is stored).
- Errors: `401 CREDENCIAL_INVALIDA` for an unknown credential; `400 VALIDACION` with `campos.credencialInstalacion` or `campos.nombreHabitacion` when one is missing.

**Capture state** — `GET /api/agente/estado-captura`, and also the response of every heartbeat
```json
{ "capturaPermitida": false, "motivo": "EN_PAUSA", "pausadaHasta": "2026-10-07T20:00:00Z", "nombreHabitacion": "Sala" }
```
`motivo` is `SIN_CONSENTIMIENTO` (no current consent; it wins over a pause), `EN_PAUSA` or `null` (allowed); `pausadaHasta` is set only during an active pause. The agent does not capture nor classify while `capturaPermitida` is `false` (CA-05.2, CA-22.1) and resumes on its own when it turns `true` (CA-22.3).

**Heartbeat** — `POST /api/agente/senal` every 30 s
```json
{ "webcamConectada": true, "deteccionConfiable": true, "versionAgente": "1.0.0" }
```
→ `200 EstadoCaptura` (the body above). A missing body counts as `webcamConectada: true`; `deteccionConfiable` and `versionAgente` are informational (unreliable detection is reported with the `deteccion_no_confiable` event). With `webcamConectada: false` the backend treats the camera as disconnected right away (CA-07.2), without waiting for missed heartbeats, and sends push `CAMARA_DESCONECTADA` once; the next heartbeat with `webcamConectada: true` brings it back (`CAMARA_RECONECTADA`, CA-07.3).

**Event** — `POST /api/agente/eventos` with the body in "Detected event" → always `202 {eventoId, alertaId | null}`.
- A repeated `eventoId` returns `202` with the same body and changes nothing (the agent retries after network errors).
- `alertaId` is `null` when the event creates or updates no alert: `deteccion_no_confiable`, a recovery with no open fall, or an event received without a current consent or during a pause (it is stored, but ignored; there is no `409`).
- An unknown `tipo` answers `400 VALIDACION`.

**Clip upload** — `POST /api/agente/eventos/{eventoId}/clip` (the body is optional)
```json
{ "contentType": "video/mp4", "tamanoBytes": 734003 }
```
→ `201 {urlSubida, cabeceras: {nombre: valor}, expiraEn}`: a pre-signed URL valid for 10 minutes. The agent then sends `PUT urlSubida` with exactly those headers (e.g. `Content-Type`; the map may be empty) and the MP4 body. The clip belongs to the alert the event created or updated; the app sees it once the storage has the object. Errors: `404 EVENTO_NO_ENCONTRADO` if the event is unknown or created no alert.

**Configuration** — `GET /api/agente/configuracion` → `200 {versionAgente, umbrales: {…}}`, where `umbrales` uses the field names of `Umbrales` in the detection package (`docs/classification-spec.md`); unknown or missing fields keep the agent's local values.
- Both come from the backend configuration: `versionAgente` from `tetengo.agente.version-publicada` (`TT_AGENTE_VERSION_PUBLICADA`, default `0.2.0`, the current agent release; the agent only logs a difference) and `umbrales` from the `tetengo.agente.umbrales` map, **empty by default**, so every agent keeps the thresholds calibrated at installation until the team publishes calibrated values.

**Token expiry:** any `401` other than `CREDENCIAL_INVALIDA` makes the agent register again with its installation credential (an expired or invalid token answers `401 SESION_EXPIRADA`). Agent tokens only open `/api/agente/**`; family members' tokens get `403` there.

**Live view stream** (`wss://…/api/agente/transmision`, proposal pending team confirmation, see `docs/BLOCKERS.md`): the agent keeps one WebSocket open with its bearer token in the handshake.
- The backend sends the text message `{"transmitir":true}` when a family member opens the live view and `{"transmitir":false}` when the last one closes it.
- While streaming, the agent sends binary frames `[8-byte big-endian ms timestamp][JPEG]`, the format of its ingestion protocol; the backend relays them unchanged to the app's `urlTransmision`.
- A new connection of the same camera replaces the previous one.
