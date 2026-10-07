"""MP4 encoding of an event clip with PyAV (FFmpeg bundled in its wheels, ADR 0008).

The packaged Windows app cannot rely on an ``ffmpeg`` executable in ``PATH``. The output is the
same as before: H.264 in MP4, ``yuv420p`` and even dimensions, at the clip's average frame rate.
"""

import io
from fractions import Fraction

import av
import cv2
import numpy as np
import numpy.typing as npt

# Fragmented MP4 can be written in one pass to memory (no seek back to move the index).
_FRAGMENTADO = {"movflags": "frag_keyframe+empty_moov"}


class ErrorCodificacionError(RuntimeError):
    """The clip's MP4 could not be built."""


def codificar_mp4(fotogramas: list[tuple[float, bytes]]) -> bytes:
    """Converts JPEG frames (instant in seconds, JPEG) into an H.264 MP4."""
    if len(fotogramas) < 2:
        raise ValueError("Se necesitan al menos dos fotogramas")
    duracion = fotogramas[-1][0] - fotogramas[0][0]
    fps = max(1.0, (len(fotogramas) - 1) / duracion) if duracion > 0 else 5.0
    imagenes = [_decodificar(jpeg) for _, jpeg in fotogramas]
    # H.264 with yuv420p requires an even width and height (a 16:9 webcam at 480p gives 853 px):
    # the odd last column or row is cropped.
    alto, ancho = imagenes[0].shape[:2]
    alto, ancho = alto - alto % 2, ancho - ancho % 2
    salida = io.BytesIO()
    try:
        with av.open(salida, mode="w", format="mp4", options=_FRAGMENTADO) as mp4:
            flujo = mp4.add_stream("libx264", rate=Fraction(fps).limit_denominator(1000))
            flujo.pix_fmt = "yuv420p"
            flujo.width, flujo.height = ancho, alto
            for imagen in imagenes:
                cuadro = av.VideoFrame.from_ndarray(imagen, format="bgr24")
                if (imagen.shape[1], imagen.shape[0]) != (ancho, alto):
                    cuadro = cuadro.reformat(width=ancho, height=alto)
                mp4.mux(flujo.encode(cuadro))
            mp4.mux(flujo.encode(None))
    except (av.error.FFmpegError, ValueError) as error:
        raise ErrorCodificacionError(f"No se pudo codificar el clip: {error}") from error
    return salida.getvalue()


def _decodificar(jpeg: bytes) -> npt.NDArray[np.uint8]:
    imagen = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
    if imagen is None:
        raise ErrorCodificacionError("Un fotograma del clip no es un JPEG válido")
    return np.ascontiguousarray(imagen, dtype=np.uint8)
