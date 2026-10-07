# Ingestion protocol (Capture Agent → Detection Module)

## Connection

```
WSS  /v1/ingesta/{camara_id}
Authorization: Bearer <TT_INGESTA_TOKEN>
```

- **Always over TLS.** In production, the reverse proxy (Nginx) terminates TLS and forwards the WebSocket to the container.
- **Wrong token:** the server closes the connection with code **1008** (*policy violation*).
- **`camara_id`:** the identifier that the Backend API assigned to the camera when the agent registered it at startup.

## Messages

One **binary message per frame**:

| Bytes | Content |
|---|---|
| 0–7 | Capture timestamp in **milliseconds since the Unix epoch**, 64-bit unsigned integer, *big-endian* |
| 8–… | **JPEG** image (480p, 5–10 fps, per the architecture) |

Python example, on the agent side:

```python
import struct, time

mensaje = struct.pack(">Q", int(time.time() * 1000)) + jpeg_bytes
await websocket.send(mensaje)
```

**Invalid message** (too short or without a JPEG): it is dropped and logged, without closing the connection.

## Why this design

- **The agent sets the timestamp,** at capture time. This way, speeds and timers (30 s, 5 min) do not depend on network latency.
- **One JPEG per frame:** it is simple to produce with OpenCV on the agent (`cv2.imencode`) and to read on the server (`cv2.imdecode`), without a media server.
