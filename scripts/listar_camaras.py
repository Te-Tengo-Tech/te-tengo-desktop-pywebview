"""Lists the webcams of this PC with their stable device ID, for installers and support.

The ID is what the installation stores to tie a room to a camera (CA-29.4); the OpenCV index
is only valid right now and changes when webcams are plugged in or the PC restarts.

Examples:
    uv run python scripts/listar_camaras.py
    uv run python scripts/listar_camaras.py --abrir   # also open each one with OpenCV
"""

import argparse

from te_tengo_captura.captura.dispositivos import (
    CAP_AVFOUNDATION,
    CAP_DSHOW,
    CAP_V4L2,
    Dispositivo,
    listar_dispositivos,
)

BACKENDS = {CAP_AVFOUNDATION: "AVFOUNDATION", CAP_DSHOW: "DSHOW", CAP_V4L2: "V4L2"}


def argumentos() -> argparse.Namespace:
    a = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    a.add_argument(
        "--abrir",
        action="store_true",
        help="Abre cada cámara con OpenCV y lee un fotograma (puede pedir permiso de cámara)",
    )
    return a.parse_args()


def probar(dispositivo: Dispositivo) -> str:
    import cv2

    captura = cv2.VideoCapture(dispositivo.indice, dispositivo.backend)
    try:
        if not captura.isOpened():
            return "no abre"
        ok, imagen = captura.read()
        if not ok or imagen is None:
            return "abre, sin fotograma"
        alto, ancho = imagen.shape[:2]
        return f"abre, {ancho}x{alto}"
    finally:
        captura.release()


def main() -> None:
    args = argumentos()
    dispositivos = listar_dispositivos()
    if not dispositivos:
        print("No se encontraron cámaras.")
        return
    for d in dispositivos:
        backend = BACKENDS.get(d.backend, str(d.backend))
        print(f"[{d.indice}] {d.nombre}  (backend {backend})")
        print(f"    ID: {d.dispositivo_id}")
        if args.abrir:
            print(f"    OpenCV: {probar(d)}")


if __name__ == "__main__":
    main()
