# Household agent contract (Te Tengo Captura)

> The team decided to process video on the household PC (MediaPipe on CPU), so the agent sends **events**, not video (ADR 0004; the only video it sends is live view, published to MediaMTX while a family member watches; the change request to the project charter is pending). Event names and fields come from the validated classifier in `te-tengo-desktop-pywebview` (`docs/classification-spec.md`).

## Authentication
Two ways, both supported (the change request «PCs, cámaras y datos de movimiento» is pending the advisor's approval, so nothing of the first one changes):
- **Installation (until now):** the project team installs the agent with a fixed configuration (household, webcam and room) and an installation credential. At startup the agent registers its camera and receives a **per-camera JWT** with the claims `hogar_id`, `camara_id` and `rol = AGENTE`. The token only works for that household (see `MULTITENANCY.md`). Since PCs exist, the installation runs on a PC of origin `INSTALACION` named «PC de la casa», which the owner can remove from the app; then its credential answers `401 CREDENCIAL_INVALIDA`.
- **PC link (US-28):** a freshly installed PC asks for a code, the owner approves it in the app, and the PC gets its own **access token** (`hogar_id`, `pc_id`, `rol = AGENTE`, 1 h) and a **refresh token** that rotates on every use. See "PC link" below.

Every agent token is checked on every request: the tokens of a PC that left the household (US-31), and of its cameras, answer **`401 PC_DESVINCULADA`** at once, before their expiry, also on the control channel's handshake. On `401 PC_DESVINCULADA` the agent stops capturing, deletes its credentials (tokens, and the installation credential if any) and shows the link code again (CA-31.1, CA-31.2).

## Endpoints (version 1, header `Api-Version: 1`)
| Method and path | Purpose | Stories |
|---|---|---|
| `POST /api/agente/camaras/registro` | Registers the camera when the agent starts, using the installation credential, and returns the camera token | US-06 (CA-06.1) |
| `GET /api/agente/estado-captura` | Current consent and pauses: the agent does not process without consent or during a pause | US-05 (CA-05.2), US-22 |
| `POST /api/agente/senal` | Periodic heartbeat; updates the time of the last signal | US-07 |
| `POST /api/agente/eventos` | Detected event (body below); idempotent by `eventoId` | US-11 to US-21 |
| `POST /api/agente/eventos/{eventoId}/clip` | Returns a pre-signed S3 PUT URL to upload the 6 s + 6 s clip | US-18 |
| `GET /api/agente/configuracion` | Current classification thresholds and agent version, so agents can update themselves | — |
| `GET /api/versiones` | The latest published version of Te Tengo Captura per system, its installer and SHA-256 (public; API contract §12) | US-43 |
| `POST /api/agente/eventos/{eventoId}/clip/puntos` | Pre-signed PUT URL for the body landmarks of the event's clip | US-36 |
| `POST /api/agente/eventos/{eventoId}/clip/puntos/ligero` | Pre-signed PUT URL for the same landmarks in the light replay format | US-36 |
| `GET /api/agente/movimientos/estado` | Whether movements may be stored, on the PC and in the cloud (camera or PC token) | US-35, US-37 |
| `POST /api/agente/movimientos` | Pre-signed PUT URL for a 5-minute movement file of the camera | US-37 |
| `POST /api/agente/movimientos/{archivoId}/confirmacion` | The file was uploaded: it enters the index | US-37 |
| `POST /api/agente/movimientos/{archivoId}/ligero` | Pre-signed PUT URL for the light replay file next to that movement file | US-37, US-39 |
| `POST /api/agente/movimientos/{archivoId}/ligero/confirmacion` | The light file was uploaded: the app can draw that file | US-37, US-39 |
| `POST /api/agente/pc/actividad` | The PC's own changes for the activity log, also those made offline, and the replays watched on the PC (PC token) | US-33, US-39 |
| `POST /api/agente/vinculacion` | PC link: asks for a code (RFC 8628 device authorization; no token) | US-28 |
| `POST /api/agente/token` | PC link: polls for the tokens, and renews them (RFC 6749 token endpoint; no token) | US-28 |
| `POST /api/agente/token/revocacion` | PC link: revokes the refresh token, which unlinks the PC (RFC 7009; no token) | US-31 |
| `GET /api/agente/pc` | The PC's link: household, older adult, who approved it, consent (PC token) | US-28 |
| `POST /api/agente/pc/senal` | The PC's heartbeat, with its version, system and automatic updates (PC token) | US-30, US-43 |
| `DELETE /api/agente/pc` | «Desvincular esta PC» (PC token); the family is notified | US-31 |
| `PUT /api/agente/pc/camaras/inventario` | The webcams the PC detects; returns their rooms and the tokens of those in use (PC token) | US-29 |
| `GET /api/agente/pc/camaras` | The PC's webcams, their rooms and tokens, e.g. after reconnecting (PC token) | US-29 |
| `GET /api/agente/ambientes` | The household's rooms and which camera is in each one (PC token) | US-29 |
| `PUT /api/agente/pc/camaras` | Installer's fallback: «Usar esta cámara» in a room from the PC (PC token) | US-29 |
| `DELETE /api/agente/pc/camaras/{camaraId}` | Installer's fallback: «Dejar de usar» from the PC (PC token) | US-29 |
| `POST /api/agente/pc/camaras/tokens` | New per-camera tokens for the PC's cameras (PC token) | US-29 |

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
- `deteccion_no_confiable` (5 min without seeing the person); its `ocurridoEn` becomes the camera's `noConfiableDesde` (API contract)

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
- `versionAgente` is the latest published Windows version of `GET /api/versiones` (below); while nothing is published there, the backend's `tetengo.agente.version-publicada` (`TT_AGENTE_VERSION_PUBLICADA`, default `0.2.0`). The agent only logs a difference: updates use `GET /api/versiones`.
- `umbrales` comes from the `tetengo.agente.umbrales` map, **empty by default**, so every agent keeps the thresholds calibrated at installation until the team publishes calibrated values.

**Updates (US-43)** — `GET /api/versiones` (no token; API contract §12) → `200 {windows, mac, apk, play, ios, pwa, paginaDescargas}`; the PC reads `windows` or `mac`: `{version, versionMinima | null, url | null, sha256 | null, tamanoBytes | null, publicadaEn | null, notas: [string]}`.
- **When:** at startup and once a day (CA-43.1), and when the person chooses «Buscar actualizaciones». Without internet it tries again at the next check; it never stops detection.
- **Windows (CA-43.2):** download `url`, check its SHA-256 against `sha256`, and only if it matches run the installer silently (`/VERYSILENT /SUPPRESSMSGBOXES /NORESTART`), which replaces the program and opens it again; configuration, link (tokens), cameras and data stay. A mismatch, a failed download or a full disk deletes the file and installs nothing.
- **Automatically (CA-43.7):** «Actualizar automáticamente», on by default on Windows, installs the new version at 03:00 (the PC's local time) with no alert in progress and no live view or preview open.
- **macOS (CA-43.3):** only the notice and `paginaDescargas`; nothing is downloaded or installed until the disk image is notarized.
- **Never during an alert or a live view** (CA-43.9): the notice and the restart wait until they end.
- **Minimum version (CA-43.8):** an installed version below `versionMinima` shows «Actualiza Te Tengo para seguir recibiendo alertas» with the way to update; detection goes on.
- **Reported:** the heartbeat sends `actualizacionAutomatica` (below) and, after an update, the PC reports `PC_ACTUALIZADA` in its activity («Activity log»).

**Token expiry:** with an installation credential, any `401` other than `CREDENCIAL_INVALIDA` and `PC_DESVINCULADA` makes the agent register again with its installation credential (an expired or invalid token answers `401 SESION_EXPIRADA`). A linked PC renews its tokens instead (see "PC link"). Agent tokens only open `/api/agente/**`; family members' tokens get `403` there.

**Which token for which endpoint:** endpoints of one camera (`senal`, `estado-captura`, `eventos`, `clip`, and the control channel of a camera) need a per-camera token; a PC's own token gets `403 TOKEN_DE_CAMARA_REQUERIDO`. The `/api/agente/pc` endpoints need the PC's own token; any other gets `403 TOKEN_DE_PC_REQUERIDO`.

## Live view (MediaMTX)
Decided by the project owner on 2026-10-07; it replaces the WebSocket JPEG relay (binary frames are no longer accepted). The video goes to **MediaMTX**, the system's live streaming service; the API only controls the agent and authorizes MediaMTX (ADR 0007 of the backend).

**Control channel:** `wss://…/api/agente/transmision`, opened with `Authorization: Bearer <camera token>` in the handshake. A linked PC also opens one with its **own access token**, so it hears `desvincular` even while it has no camera in use; that channel only carries messages about the PC.
- The agent keeps one connection open, and reconnects with backoff. A `401` follows the "Token expiry" rule above: register again. A new connection of the same camera replaces the previous one.
- Messages are **text JSON only**, from the API to the agent:

| Message | When |
|---|---|
| `{"preparar":true}` | Live view v3: a member opened the camera screen in the app (`POST /api/vista-en-vivo/preparar`), so a live view may start soon. Never sent while the camera is already transmitting. Agents that do not know it ignore it (it carries neither `transmitir` nor `modo`) |
| `{"transmitir":true,"urlPublicacion":"rtsp://…/camaras/<camaraId>","usuario":"agente","clave":"<publish token>","modo":"VIDEO"}` | The first open live view session of the camera starts. Also on every connection while sessions are open, with a **new** `clave` (the previous one stops working) |
| `{"modo":"VIDEO_CON_POSTURA"}` | The mode changes during a transmission |
| `{"transmitir":false}` | The last session ends or expires, the camera is paused, or the consent is revoked. On pause and revocation the API also disconnects the publisher through MediaMTX |
| `{"camara":{…}}` | PC channel only: the owner assigned, moved or stopped using a webcam, or renamed its room (see "Cameras of a linked PC") |
| `{"buscarCamaras":true}` | PC channel only: «Buscar de nuevo» in the app (CA-29.6): look for webcams and report them with `PUT /api/agente/pc/camaras/inventario` |
| `{"desvincular":true}` | The PC was removed from the household (US-31). Sent on the PC's own channel and on each of its cameras' channels, which the API then closes with code `4001`. The agent stops capturing, deletes its credentials and shows the link code (CA-31.1) |

**Preparing (`preparar`, live view v3):** the agent warms up **only what stays on the PC**, so that the publication starts at once on `transmitir`: open the capture at the live view rate in memory, create the H.264 encoder, resolve the MediaMTX host and, if it can be done without publishing, open the TLS connection. **No frame leaves the PC before `transmitir`** (privacy rule of the product: video leaves the PC only during a live view); an RTSP publish session cannot be opened without sending media, so it is not opened early. The warm state lasts at most 60 s (implementation choice) and is discarded on timeout, on `{"transmitir":false}`, on a pause, on a revoked consent (`capturaPermitida: false`) and when the agent stops. A new `preparar` restarts the 60 s.

**Publishing:**
- The agent publishes to `urlPublicacion` with `usuario` and `clave` as the RTSP credentials.
  - Locally the URL is RTSP over TCP: `rtsp://localhost:8554/camaras/<camaraId>`.
  - Production may send RTSPS (`rtsps://<host>:8322/…`): the agent opens whatever URL it gets.
- Video: H.264, no audio, 480p, low latency (`zerolatency`), with PyAV. Live view v3: **Constrained Baseline** profile (no B-frames: every browser and WebRTC stack decodes it, and MediaMTX offers H.264 over WebRTC only as `profile-level-id=42e01f`), about **15 fps** at a constant rate taken from the webcam independently of the detection rate (detection keeps its own 480p, 8 fps sampling), and a **keyframe every 0.5 s** (GOP = fps / 2), the first frame of every publication being a keyframe: WebRTC and LL-HLS viewers start at a keyframe. Earlier agents publish the 8 fps detection frames with a GOP of about 1 s; MediaMTX serves either.
- The app plays the stream over WebRTC (WHEP) first and LL-HLS as the fallback; both come from the same publication, so nothing changes for the agent.
- The agent stops publishing at once on `{"transmitir":false}`, and also whenever its own capture state does not allow capture (`capturaPermitida: false`).
- MediaMTX asks the API before every publish (`POST /api/interno/mediamtx/autorizar`, internal). The API allows it only for the camera's own path, user `agente` and the current `clave`, while capture is allowed.

**Modes** (`modo`), drawn by the agent on the frames it publishes, from the MediaPipe landmarks it already computes. A mode applies to the camera's stream, so every viewer sees the same one (implementation choice):
- `VIDEO` (default): the camera frame.
- `VIDEO_CON_POSTURA`: the camera frame with the skeleton drawn on top.
- `SOLO_POSTURA`: the skeleton on a plain neutral background, in the brand colours. **No camera pixels**: no image of the home leaves the PC.

## PC link (US-28, US-30, US-31)
OAuth 2.0 Device Authorization Grant (RFC 8628) with rotating refresh tokens (RFC 9700), implemented by the API (ADR 0009). The three OAuth endpoints follow the RFCs, not the rest of this contract: **requests are `application/x-www-form-urlencoded`**, responses are snake_case JSON with `Cache-Control: no-store`, and **errors are `{"error": "…", "error_description": "…"}`** (RFC 6749 §5.2), HTTP 400 except `invalid_client` (401). No bearer token is sent to them. `client_id` is always `te-tengo-captura`.

**Limits per address.** Device authorization and the token endpoint are public, so the API limits them per client address **[implementation choice]**: 10 code requests per minute and 60 per hour, and 60 token requests per minute. Over a limit they answer `429` with `Retry-After` (seconds) and an `application/problem+json` body with `codigo: DEMASIADAS_SOLICITUDES`; on a device code poll the body also carries `"error": "slow_down"` (RFC 8628 §3.5). One PC polling every `interval` never reaches them; several PCs behind one address might. On a `429` the PC waits at least `Retry-After` (as for any `429`, it may wait longer) and keeps its code, which stays valid.

**1. Ask for a code** — `POST /api/agente/vinculacion`
```
client_id=te-tengo-captura&nombre_pc=Sala-Rosa&sistema_operativo=Windows%2011%20Home&version_agente=0.5.0
```
- `nombre_pc` (required, 1–60 characters; the computer's name), `sistema_operativo` (optional, up to 60) and `version_agente` (optional, up to 40) are what the app shows before approving (CA-28.4). `scope` is ignored.
- → `200`
```json
{ "device_code": "<43 chars, secret>", "user_code": "KQWT-MXHD",
  "verification_uri": "https://app.tetengo.reqsai.tech/vincular",
  "verification_uri_complete": "https://app.tetengo.reqsai.tech/vincular?codigo=KQWT-MXHD",
  "expires_in": 600, "interval": 5 }
```
- The PC shows a QR of `verification_uri_complete`, the `user_code` in large type, `verification_uri`, and a countdown of `expires_in` (D-28.1). **`device_code` is a secret: never show it, log it or write it to disk.**
- When the code expires the PC asks for a new one on its own (CA-28.3). Errors: `invalid_request` (missing `nombre_pc` or `client_id`), `invalid_client`.

**2. Poll** — `POST /api/agente/token` every `interval` seconds
```
grant_type=urn:ietf:params:oauth:grant-type:device_code&device_code=<device_code>&client_id=te-tengo-captura
```
| Answer | Meaning | The PC |
|---|---|---|
| `400 {"error":"authorization_pending"}` | Nobody approved it yet | keeps polling every `interval` |
| `400 {"error":"slow_down"}` | Polled sooner than the interval | adds 5 s to its interval, for good (RFC 8628 §3.5) |
| `400 {"error":"access_denied"}` | «No reconozco esta PC» in the app | shows D-28.5 and «Mostrar otro código» |
| `400 {"error":"expired_token"}` | The 10 minutes ran out | asks for a new code (step 1) |
| `400 {"error":"invalid_grant"}` | Unknown or already used device code | asks for a new code |
| `200` (below) | Approved | stores the tokens and stops polling |

```json
{ "access_token": "<JWT>", "token_type": "Bearer", "expires_in": 3600,
  "refresh_token": "<43 chars>", "pc_id": "0192…", "hogar_id": "0192…" }
```
- **Store both tokens in the operating system's credential store** (Windows Credential Manager), never in files (change request 2.1). The device code works once.

**3. Use and renew.**
- The access token (claims `sub` = `pc_id`, `hogar_id`, `pc_id`, `rol = AGENTE`) lasts 1 h **[implementation choice]**; it opens the `/api/agente/pc` endpoints and the PC's control channel. The cameras of a linked PC use per-camera tokens with the same claims plus `camara_id` (see "Cameras of a linked PC").
- Renew it before it expires, or on `401 SESION_EXPIRADA`, with `POST /api/agente/token`:
```
grant_type=refresh_token&refresh_token=<refresh_token>&client_id=te-tengo-captura
```
  → `200` with the same body as step 2, **including a new `refresh_token`**: replace the stored one in the same step. Each refresh token works **once**: presenting an old one again revokes every token of the PC and unlinks it (RFC 9700 §4.14.2), so never retry a refresh with a token that already got an answer.
- Each refresh token lasts 90 days: a PC that renews at least once every 90 days stays linked, through restarts, network changes and outages under 90 days (CA-28.7). After 90 days without connecting, or once unlinked, renewing answers `invalid_grant`: delete the credentials and show the link code (step 1), with the banner «Esta PC estuvo más de 90 días sin conexión» when the PC knows it was offline that long.

**The PC's own endpoints** (its access token):
- `GET /api/agente/pc` → `200 PcDelAgente = {pcId, hogarId, nombre, nombreAdultoMayor, vinculadaEn, vinculadaPor | null, consentimientoVigente}`. D-28.4: «Esta PC quedó vinculada a la casa de Rosa Huamán · Aprobada por Carmen a las 10:31»; with `consentimientoVigente: false` the PC says it waits for the consent and sends no video (CA-28.1). `vinculadaPor` is the approver's name, null for installations.
- `POST /api/agente/pc/senal` every 30 s, like the cameras' heartbeat, with an optional `{versionAgente, sistemaOperativo, actualizacionAutomatica}` → `200 PcDelAgente`. It keeps the PC «En línea» in the app even with no camera in use (CA-30.2); camera heartbeats count too. `actualizacionAutomatica` (boolean, US-43, CA-43.7): whether «Actualizar automáticamente» is on; the app shows it as `Pc.actualizacionAutomatica` (omitted keeps the last value).
- `DELETE /api/agente/pc` → `204`: «Desvincular esta PC» (CA-31.3). The API revokes the PC's tokens, retires its cameras and sends push `PC_DESVINCULADA` to the family; the PC then deletes its credentials and shows the link code. Add `?datosLocalesBorrados=true` when the person also checked «Borrar también los datos guardados en esta PC» (CA-31.6): the PC deletes its data folder (movements, video and clips) itself; the API only records it in the activity log (`DATOS_LOCALES_ELIMINADOS`). Without it the folder stays, encrypted. Revoking the refresh token does the same and works without a valid access token:

**Unlink with the refresh token** — `POST /api/agente/token/revocacion` (RFC 7009)
```
token=<refresh_token>&token_type_hint=refresh_token&client_id=te-tengo-captura
```
(add `&datos_locales_borrados=true` for CA-31.6, as above)
→ always `200` with an empty body, also for an unknown or already revoked token (RFC 7009 §2.2). Errors: `invalid_request`, `invalid_client`.

**Removed from the app (CA-31.1, CA-31.2).** The PC hears it as `{"desvincular":true}` on its control channels if it is online, or as `401 PC_DESVINCULADA` (or `invalid_grant` when renewing) at its next request. Either way: stop capturing at once, delete the credentials and show the link code, with D-31.2 («Esta PC se quitó de la casa de Rosa Huamán»).

## Cameras of a linked PC (US-29, US-30)
Product decision of 2026-10-10: **the owner assigns the cameras to rooms from the phone.** The PC reports the webcams it detects, the app shows them in «Elige las cámaras» and assigns them, and the PC follows: **only cameras in use capture**. Each webcam is known by the **operating system's unique device id**, not its index, so plugging another webcam or restarting does not change which camera watches each room (CA-29.4). The PC's own preview stays local (CA-29.1). With the PC's own access token:

**1. Report the webcams** — `PUT /api/agente/pc/camaras/inventario`, at startup and whenever a webcam is plugged in or out (the whole list each time; an empty list when it finds none, CA-29.6):
```json
{ "webcams": [
  { "dispositivoId": "\\\\?\\usb#vid_046d&pid_0825#…", "nombreDispositivo": "Logitech C920", "conectada": true },
  { "dispositivoId": "…", "nombreDispositivo": "Webcam USB HD", "conectada": true } ] }
```
`dispositivoId` up to 300 characters, `nombreDispositivo` up to 100, at most 32 webcams; `conectada` defaults to true. New webcams are added «sin usar»; webcams missing from the list count as unplugged and **keep their room** (CA-29.5). → `200 [CamaraDeLaPc]`, every webcam of the PC:
```json
{ "camaraId": "0192…", "dispositivoId": "…", "nombreDispositivo": "Logitech C920",
  "enUso": true, "conectada": true, "ambienteId": "0192…", "nombreHabitacion": "Dormitorio",
  "estadoConexion": "EN_LINEA", "pausadaHasta": null,
  "token": "<per-camera JWT>", "expiraEn": "2026-10-10T16:31:00Z" }
```
For `enUso: false` the room fields and `token` are null. Start a worker for each camera in use with its token (heartbeat every 30 s, `estado-captura`, events, clips, its control channel), exactly like an installation's camera; its `nombreHabitacion` is what the alerts say.

**2. Follow the owner's changes** on the PC's own control channel (see "Live view"): `{"camara": {"camaraId", "dispositivoId", "nombreDispositivo", "enUso", "ambienteId", "nombreHabitacion"}}` when the owner assigns a webcam, moves it, renames its room or stops using it. On `enUso: true` get its token with `POST /api/agente/pc/camaras/tokens` and start it; on `enUso: false` stop it at once (its token already answers `401 PC_DESVINCULADA`). While offline the PC misses them: **after every (re)connection call `GET /api/agente/pc/camaras`** (same body as step 1, with the tokens of the cameras in use) and reconcile.

**3. Previews.** The owner may preview any webcam, also one «sin usar», to recognise it (the app's `POST /api/camaras/{id}/vista-previa`). A camera in use gets the usual `transmitir` on its own channel. A webcam «sin usar» has no channel of its own: the PC's channel gets the same live view messages with the camera and device ids added, `{"transmitir":true,"urlPublicacion":"…/camaras/<camaraId>","usuario":"agente","clave":"…","modo":"VIDEO","camaraId":"…","dispositivoId":"…"}`, then `{"transmitir":false,"camaraId":"…","dispositivoId":"…"}` (and `{"modo":…,"camaraId":…,"dispositivoId":…}`). Publish that webcam to `urlPublicacion` exactly as a live view (nothing leaves the PC before `transmitir`; stop on `transmitir:false`). Previews last 2 minutes at most.

**Other endpoints:**
- `POST /api/agente/pc/camaras/tokens` → `200 [CamaraDeLaPc]` with a new token for each camera in use. Camera tokens last as long as the PC's access token (1 h): renew them right after renewing the PC's tokens.
- `GET /api/agente/ambientes` → `200 [Ambiente]` (API contract §9): the rooms and the camera in use in each, on this PC or another (`pcNombre`).
- **Installer's fallback, «Elegir aquí»** (CA-29.8; the owner's app is the normal way), with the same rules as the app (CA-29.2 to CA-29.4) and a preview that only shows on the PC; the assignment appears in the app. When the app and the PC both change a camera, the last change wins, and the activity log records where each came from: `PUT /api/agente/pc/camaras` with `{dispositivoId, nombreDispositivo, ambienteId | nombreAmbiente}` assigns a webcam from the PC (an upsert by `dispositivoId`; → `200 CamaraDeLaPc` with its token), and `DELETE /api/agente/pc/camaras/{camaraId}` stops using one. Errors: `409 AMBIENTE_OCUPADO {ambiente, camara: {id, pcId, pcNombre, nombreDispositivo}}` (CA-29.3: «Ya hay una cámara en el ambiente Sala (PC Sala-Rosa). Por ahora, cada ambiente usa una sola cámara.»), `422 AMBIENTE_NO_PERMITIDO` («Por privacidad, Te Tengo no admite cámaras en el baño.»), `422 AMBIENTE_NOMBRE_VACIO` (CA-29.2), `422 AMBIENTE_NOMBRE_MUY_LARGO`, `404 AMBIENTE_NO_ENCONTRADO`, `404 CAMARA_NO_ENCONTRADA` (a camera of another PC), `400 VALIDACION`.
- **A disconnected camera stays in its room** (CA-29.5): report it with `webcamConectada: false` on its heartbeat, as today, and in the next inventory; the room is not given to another camera and the app warns as in CA-07.2.

## Movement data (US-35 to US-38)
Body landmarks only, never images (ADR 0010). **Nothing is stored, on the PC or in the cloud, without the consent to store movements** (CA-35.3); detection and alerts work the same without it.

**May I store?** — `GET /api/agente/movimientos/estado` (camera or PC token) → `200 {consentimientoVigente, guardarEnLaPc, guardarEnLaNube, retencionDias | null, versionTextoVigente}`.
- `guardarEnLaPc` is the consent: the local storage options (US-38) are disabled without it, with the reason «Requiere el permiso de Rosa para guardar movimientos. Se registra en la app Te Tengo.».
- `guardarEnLaNube`: the consent and a cloud retention chosen by the owner (`retencionDias` 7, 30, 90 or 365). Ask at startup, every 5 minutes before an upload, and after any `409` of the endpoints below. When the consent turns off, stop storing at once and ask the person at the PC whether to delete the local movements too (CA-35.4).

**Upload a movement file** (CA-37.2), one per camera every 5 minutes of capture: Parquet with zstd, the columns of the PC's own format (33 quantized MediaPipe points, time, θ, P, v, phase). In the agent's queue it goes in the lowest-priority lane, after urgent events, other events and clips; files made without internet wait on disk and are uploaded when it returns (CA-37.3).
1. `POST /api/agente/movimientos` (camera token)
```json
{ "desde": "2026-10-10T15:40:00Z", "hasta": "2026-10-10T15:45:00Z",
  "tamanoBytes": 412345, "sha256": "<64 hex>", "fotogramas": 2400 }
```
   → `201 {archivoId, urlSubida, cabeceras: {nombre: valor}, expiraEn}` (10 minutes). The object key is `movimientos/<hogar>/<camara>/YYYY/MM/DD/HH/mm.parquet` from `desde` in UTC: one file per camera and start.
2. `PUT urlSubida` with exactly those headers (`Content-Type: application/vnd.apache.parquet`) and the file. The bytes go straight to the storage, never through the API.
3. `POST /api/agente/movimientos/{archivoId}/confirmacion` → `200 {archivoId, estado: "DISPONIBLE", tamanoBytes}`: the file enters the index. `409 ARCHIVO_NO_SUBIDO`: the storage does not have it; upload it again.
- Errors of step 1: `409 SIN_CONSENTIMIENTO_DE_MOVIMIENTOS` or `409 MOVIMIENTOS_EN_LA_NUBE_DESACTIVADOS` (stop uploading and check the state), `422 MOVIMIENTOS_FUERA_DEL_PLAZO` (already older than the retention: drop it from the queue), `409 ARCHIVO_YA_SUBIDO {archivoId}` (it is already in the index: drop it), `400 VALIDACION` (`hasta` after `desde`, at most 10 minutes, `desde` not ahead of the server's clock by more than 1 minute, `tamanoBytes` up to 50 MB, `sha256` 64 hex characters). Asking again for a file still pending returns a new URL for the same `archivoId`.
- If the consent is revoked between the upload and the confirmation, the confirmation answers `409 SIN_CONSENTIMIENTO_DE_MOVIMIENTOS` and the API deletes the object.

**Light replay file** (US-39): after the Parquet file is in the index, the same frames in the light format below, so the app can draw them on every platform. Same lane, right after its Parquet file; written from the same rows, kept, encrypted and deleted on the PC together with it.
4. `POST /api/agente/movimientos/{archivoId}/ligero` (camera token) `{"tamanoBytes": 256123, "sha256": "<64 hex>"}` → `201 {urlSubida, cabeceras, expiraEn}` (10 minutes); the object key is the Parquet file's with `.ttmov` (`…/mm.ttmov`). `archivoId` comes from step 1, or from the body of its `409 ARCHIVO_YA_SUBIDO` when the Parquet file was uploaded before.
5. `PUT urlSubida` with exactly those headers (`Content-Type: application/gzip`) and the file.
6. `POST /api/agente/movimientos/{archivoId}/ligero/confirmacion` → `200 {archivoId, tamanoBytes}`. `409 ARCHIVO_NO_SUBIDO`: the storage does not have it; upload it again.
- Errors of step 4: `404 ARCHIVO_NO_ENCONTRADO` (not this camera's file, or deleted meanwhile: drop the light file), `409 ARCHIVO_YA_SUBIDO` (the light file is already in the index: drop it), `409 SIN_CONSENTIMIENTO_DE_MOVIMIENTOS` or `409 MOVIMIENTOS_EN_LA_NUBE_DESACTIVADOS` (like step 1), `400 VALIDACION` (`tamanoBytes` up to 50 MB, `sha256` 64 hex characters). A revocation before step 6 deletes the object like step 3. An older API without these paths answers `404` without `codigo`: upload the Parquet file only.
- The light file is deleted with its Parquet file (retention, revocation, the day's cleanup of unconfirmed uploads).

**Landmarks of a clip** (US-36): after uploading the clip of an event, `POST /api/agente/eventos/{eventoId}/clip/puntos` (camera token, no body) → `201 {urlSubida, cabeceras, expiraEn}`; `PUT` the landmarks of the clip's 12 seconds as Parquet with those headers. The app draws them over the clip, synchronized by time. `409 SIN_CONSENTIMIENTO_DE_MOVIMIENTOS` without the consent (do not upload them); `404 EVENTO_NO_ENCONTRADO` like the clip. They are deleted with their clip (CA-36.3). Then `POST /api/agente/eventos/{eventoId}/clip/puntos/ligero` (camera token, no body) → `201 {urlSubida, cabeceras, expiraEn}` (key `clips/<alerta>.landmarks.ttmov`, `Content-Type: application/gzip`); `PUT` the same rows in the light format below (`t0Ms` the clip's start, 6 s before the event, `duracionMs` 12000). Same errors; there is no confirmation: the app gets it when the storage has it. Deleted with the clip and its Parquet landmarks.

### Light replay format (TTMOV v1)
The app cannot read Parquet on every platform (ADR 0011 of the backend), so next to each Parquet file the PC uploads the same frames in this small format, made from the same rows. The Parquet file stays the source for analysis (US-40); the light file only serves to draw the skeleton (US-36, US-39). Same file for a 5-minute window and for a clip's 12 seconds.
- **Container:** one gzip member (RFC 1952; deflate, RFC 1951) holding the payload below; header `MTIME` 0, no file name. Content type `application/gzip`. Readers decompress the whole file, then check the magic.
- **Byte order:** little-endian. `u8`, `u16`, `u32`: unsigned; `i32`, `i64`: two's complement.
- **Header** (24 bytes):

| Offset | Type | Field | Value |
|---|---|---|---|
| 0 | 4 bytes | `magia` | ASCII `TTMV` (`54 54 4D 56`) |
| 4 | u8 | `version` | `1`; a reader rejects any other |
| 5 | u8 | `banderas` | bit 0 `Z`: each pose carries `z`; bits 1–7 are 0 (a reader rejects a file with any of them set) |
| 6 | u8 | `fpsObjetivo` | the camera's analysis rate, `8` |
| 7 | u8 | `puntos` | landmarks per pose, `33` (MediaPipe Pose order) |
| 8 | i64 | `t0Ms` | start of the file, UTC epoch milliseconds (`desde`) |
| 16 | u32 | `duracionMs` | `hasta − desde`: the file covers `[t0Ms, t0Ms + duracionMs)` |
| 20 | u32 | `fotogramas` | number of frames that follow |

- **Frames**, `fotogramas` times, in the Parquet file's row order:

| Type | Field | Meaning |
|---|---|---|
| i32 | `dtMs` | the frame's time minus the previous frame's (the first: minus `t0Ms`); the frame is at `t0Ms + Σ dtMs`. Negative only if the PC's clock stepped back |
| u8 | `estado` | bit 0: a person (pose) is in the frame; bits 1–2 `fase`: 0 `normal`, 1 `inicio_caida`, 2 `en_el_suelo`; bits 3–5 `evento` detected on this frame: 0 none, 1 `caida`, 2 `caida_confirmada`, 3 `movimiento_inestable`, 4 `recuperacion`, 5 `deteccion_no_confiable`; bits 6–7 are 0. A reader treats an unknown `fase` or `evento` value as `normal` / none |
| `puntos` × u16 | `dx` | only with a pose: `x` of each landmark, as a delta |
| `puntos` × u16 | `dy` | only with a pose: `y`, as a delta |
| `puntos` × u8 | `dv` | only with a pose: visibility, as a delta |
| `puntos` × u16 | `dz` | only with a pose and the `Z` flag: `z` (its int16 bit pattern), as a delta |

- **Deltas:** each value is the difference with the same landmark's value in the **previous frame that had a pose in this file**, modulo 2¹⁶ (u16) or 2⁸ (u8); for the first pose of the file the previous values are 0. So `x = (xAnterior + dx) mod 65536`, and so on. Frames without a pose carry no landmarks and do not reset the reference.
- **Quantization**, the same integers as the Parquet file (`q` stored, `c` MediaPipe's value): `x`, `y`: `c = q / 65535 × 2 − 0.5` (range −0.5 to 1.5, normalized to the image; 0 is the left or top edge); visibility: `c = q / 255`; `z` (int16): `c = q / 8192`. A landmark with visibility below 0.5 should not be drawn.
- **Names:** the object key is the Parquet file's with `.ttmov` instead of `.parquet` (`movimientos/<hogar>/<camara>/YYYY/MM/DD/HH/mm.ttmov`; a clip's `clips/<alerta>.landmarks.ttmov`).
- **Sizes** (measured, 5 minutes with a person in the image 86 % of the frames): Parquet 459 KB, light file 257 KB; about 132 MB and 74 MB per camera and day.

## Activity log (US-32, US-33)
The API logs on its own every change it sees (the PC linked or unlinked, a camera's room, «Dejar de usar», pauses, consents, the cloud retention). The PC reports the changes only it knows about, which it also keeps in its local log (shown «Pendiente de enviar» until sent, CA-33.3):

`POST /api/agente/pc/actividad` (PC token)
```json
{ "cambios": [
  { "id": "0192…", "tipo": "MODO_AVANZADO_ACTIVADO", "ocurridoEn": "2026-10-10T16:02:00Z" },
  { "id": "0192…", "tipo": "GUARDADO_LOCAL_CAMBIADO", "ocurridoEn": "2026-10-10T16:05:00Z",
    "objeto": "Video continuo", "valorAnterior": "No", "valorNuevo": "Sí, 7 días" },
  { "id": "0192…", "tipo": "REPETICION_VISTA", "ocurridoEn": "2026-10-10T16:20:00Z",
    "camaraId": "0192…", "objeto": "Sala", "momentoDesde": "2026-10-10T15:36:00Z",
    "momentoHasta": "2026-10-10T15:46:00Z", "duracionSegundos": 180 } ] }
```
→ `200 {registrados, repetidos}`.
- `tipo`: `MODO_AVANZADO_ACTIVADO`, `MODO_AVANZADO_DESACTIVADO` (CA-32.1), `GUARDADO_LOCAL_CAMBIADO` (US-38: folder, a type on or off, its period, the space limit; one entry per setting), `DATOS_LOCALES_ELIMINADOS` (e.g. the local movements after a revocation, CA-35.4), `PC_ACTUALIZADA` (US-43, CA-43.2: after installing an update, `objeto` `Te Tengo Captura`, `valorAnterior` the old version and `valorNuevo` the new one), `ACTUALIZACION_AUTOMATICA_ACTIVADA` / `ACTUALIZACION_AUTOMATICA_DESACTIVADA` (CA-43.7: «Actualizar automáticamente», `objeto` `Actualizar automáticamente`) or `REPETICION_VISTA` (below). Anything else is `400 VALIDACION` (`campos["cambios[i].tipo"]`).
- `REPETICION_VISTA` (US-39, CA-39.3): someone replayed a camera's movements **on the PC** («Ver qué pasó»). Reported under the same rule as the app: only when the replay was played or scrubbed, not when it was only opened. `ocurridoEn` is when the replay was opened; `camaraId` a camera of this PC (otherwise `campos["cambios[i].camaraId"]`); `objeto` the room as the PC showed it (optional: the camera's current room); `momentoDesde` < `momentoHasta` the moment replayed, not in the future (`campos["cambios[i].momentoDesde"]` / `["…momentoHasta"]`); `duracionSegundos` (≥ 0) how long it was watched (`campos["cambios[i].duracionSegundos"]`). The PC has no member identity: the log says it was done on the PC. The API stores the moment as an ISO-8601 interval in `valorAnterior` (`"2026-10-10T15:36:00Z/2026-10-10T15:46:00Z"`) and the seconds in `valorNuevo` (`"180"`), and the app shows it in «Actividad» and in the access log (API contract §10). These four fields are ignored for the other types.
- `id`: a UUID the PC generates once per change; sending a change again (after a timeout, or the whole offline queue) stores it once (`repetidos`). `ocurridoEn`: when it happened on the PC, not more than 5 minutes ahead of the server. `objeto` up to 120 characters, `valorAnterior` and `valorNuevo` up to 200. At most 100 changes per request.
- The family sees them in the app as «Desde la PC Sala-Rosa: …»; the PC shows the household's log with `GET /api/actividad` only through the app (the PC has no member token).
