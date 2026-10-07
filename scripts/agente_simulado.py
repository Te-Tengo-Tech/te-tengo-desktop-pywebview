"""Simulated Capture Agent: sends the webcam (or a video) to the worker over WebSocket.

It does what Te Tengo Captura will do: downscales the video to 480p and 5-10 fps, compresses
it as JPEG and sends it with the protocol in docs/ingestion-protocol.md. The token is read from
your .env.

Requirements: the worker running (make ejecutar) and TT_CLASIFICACION__VELOCIDAD_DESCENSO_MIN
defined in .env; otherwise, the worker closes the connection with code 1011.

Examples:
    uv run python scripts/agente_simulado.py
    uv run python scripts/agente_simulado.py --video caida.mp4 --recorte 320,0,320,240
"""

import argparse
import sys
import time
from pathlib import Path

import cv2
from websockets.exceptions import ConnectionClosed
from websockets.sync.client import connect

from detection_worker.config import cargar_settings
from detection_worker.ingesta import protocolo

ALTO_MAX = 480


def leer_recorte(texto: str | None) -> tuple[int, int, int, int] | None:
    """Converts an "x,y,width,height" string into a tuple."""
    if not texto:
        return None
    x, y, ancho, alto = (int(n) for n in texto.split(","))
    return x, y, ancho, alto


def main() -> int:
    a = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    fuente = a.add_mutually_exclusive_group()
    fuente.add_argument("--camara", type=int, default=0, help="Índice de la webcam (por defecto 0)")
    fuente.add_argument("--video", type=Path, help="Archivo de video en lugar de la webcam")
    a.add_argument("--url", default="ws://localhost:8001", help="Dirección del worker")
    a.add_argument("--camara-id", default="camara-local", help="Identificador de la cámara")
    a.add_argument("--fps", type=float, default=8.0, help="Fotogramas por segundo a enviar")
    a.add_argument("--recorte", help="Región x,y,ancho,alto a enviar (URFD: 320,0,320,240)")
    args = a.parse_args()

    token = cargar_settings().ingesta_token.get_secret_value()
    recorte = leer_recorte(args.recorte)
    captura = cv2.VideoCapture(str(args.video) if args.video else args.camara)
    if not captura.isOpened():
        print(
            "No se pudo abrir la fuente de video. En macOS, da permiso de cámara a tu terminal.",
            file=sys.stderr,
        )
        return 1

    url = f"{args.url}/v1/ingesta/{args.camara_id}"
    periodo = 1 / args.fps
    fps_video = captura.get(cv2.CAP_PROP_FPS) or 30.0
    origen_ms = int(time.time() * 1000)
    indice, siguiente, enviados = 0, 0.0, 0
    try:
        with connect(url, additional_headers={"Authorization": f"Bearer {token}"}) as ws:
            print(f"Conectado a {url}. Enviando a {args.fps} fps (Ctrl+C para terminar).")
            while True:
                inicio = time.monotonic()
                ok, imagen = captura.read()
                if not ok:
                    break
                if args.video:
                    # Same as the validation: the frame is taken when the video time reaches
                    # the next 1/fps instant, and that time is used as the timestamp.
                    t_video = indice / fps_video
                    indice += 1
                    if t_video + 1e-9 < siguiente:
                        continue
                    siguiente += periodo
                    marca_ms = origen_ms + round(t_video * 1000)
                else:
                    marca_ms = int(time.time() * 1000)
                if recorte:
                    x, y, w, h = recorte
                    imagen = imagen[y : y + h, x : x + w]
                alto, ancho = imagen.shape[:2]
                if alto > ALTO_MAX:
                    imagen = cv2.resize(imagen, (round(ancho * ALTO_MAX / alto / 2) * 2, ALTO_MAX))
                ok, jpeg = cv2.imencode(".jpg", imagen, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if ok:
                    ws.send(protocolo.codificar(marca_ms, jpeg.tobytes()))
                    enviados += 1
                time.sleep(max(0.0, periodo - (time.monotonic() - inicio)))
    except ConnectionClosed as cierre:
        print(
            f"El worker cerró la conexión: código {cierre.rcvd.code if cierre.rcvd else '?'} "
            f"({cierre.rcvd.reason if cierre.rcvd else ''})",
            file=sys.stderr,
        )
        return 1
    except KeyboardInterrupt:
        pass
    finally:
        captura.release()
    print(f"Fin. Fotogramas enviados: {enviados}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
