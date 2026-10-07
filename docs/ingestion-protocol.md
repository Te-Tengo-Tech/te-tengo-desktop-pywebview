# Protocolo de ingesta (Agente de captura → Módulo de detección)

## Conexión

```
WSS  /v1/ingesta/{camara_id}
Authorization: Bearer <TT_INGESTA_TOKEN>
```

- **Siempre por TLS.** En producción, el proxy inverso (Nginx) termina el TLS y reenvía el WebSocket al contenedor.
- **Token incorrecto:** el servidor cierra la conexión con el código **1008** (*policy violation*).
- **`camara_id`:** es el identificador que el Backend API asignó a la cámara cuando el agente la registró al iniciar.

## Mensajes

Un **mensaje binario por fotograma**:

| Bytes | Contenido |
|---|---|
| 0–7 | Instante de captura en **milisegundos desde la época Unix**, entero sin signo de 64 bits, *big-endian* |
| 8–… | Imagen **JPEG** (480p, 5–10 fps, según la arquitectura) |

Ejemplo en Python, del lado del agente:

```python
import struct, time

mensaje = struct.pack(">Q", int(time.time() * 1000)) + jpeg_bytes
await websocket.send(mensaje)
```

**Mensaje inválido** (muy corto o sin un JPEG): se descarta y se registra en el log, sin cerrar la conexión.

## Por qué así

- **La marca de tiempo la pone el agente,** en el momento de la captura. Así, las velocidades y los tiempos (30 s, 5 min) no dependen de la latencia de la red.
- **JPEG por fotograma:** es simple de producir con OpenCV en el agente (`cv2.imencode`) y de leer en el servidor (`cv2.imdecode`), sin un servidor de medios.
