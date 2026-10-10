"""MP4 encoding of an event clip with PyAV (FFmpeg bundled in its wheels, ADR 0008).

The packaged Windows app cannot rely on an ``ffmpeg`` executable in ``PATH``. The output is
H.264 in a regular (not fragmented) MP4 whose index, the ``moov`` box, comes before the media
data (``+faststart``), so phones can play it and seek in it right away; Safari/AVPlayer and
ExoPlayer seek poorly in a fragmented MP4 without an index.

Encoder settings: ``yuv420p`` and even dimensions, the **Constrained Baseline** profile (no
B-frames, no CABAC: the one H.264 profile every decoder supports, the same as the live view), a
constant frame rate (the clip's average one) and one keyframe every half second (``GOP_S``)
with no extra keyframes on scene changes, so seeking lands at most half a second away.

FFmpeg's ``faststart`` reopens the output by its file name to move the index, which an in-memory
buffer does not have: the clip is written to a temporary file in ``directorio`` (the outbox's
clip directory in the app) and deleted right after it is read back, so no frame stays on disk
besides the clip itself.
"""

import os
import tempfile
from fractions import Fraction
from pathlib import Path

import av
import cv2
import numpy as np
import numpy.typing as npt

GOP_S = 0.5
PERFIL = "baseline"  # libx264 only produces Constrained Baseline for it
_FASTSTART = {"movflags": "+faststart"}
_PREFIJO_TEMPORAL = ".codificando-"


class ErrorCodificacionError(RuntimeError):
    """The clip's MP4 could not be built."""


def codificar_mp4(fotogramas: list[tuple[float, bytes]], directorio: Path | None = None) -> bytes:
    """Converts JPEG frames (instant in seconds, JPEG) into an H.264 MP4.

    ``directorio`` holds the temporary file while it is encoded (the system's temporary
    directory when ``None``); the file is always deleted before returning.
    """
    if len(fotogramas) < 2:
        raise ValueError("Se necesitan al menos dos fotogramas")
    duracion = fotogramas[-1][0] - fotogramas[0][0]
    fps = max(1.0, (len(fotogramas) - 1) / duracion) if duracion > 0 else 5.0
    imagenes = [_decodificar(jpeg) for _, jpeg in fotogramas]
    # H.264 with yuv420p requires an even width and height (a 16:9 webcam at 480p gives 853 px):
    # the odd last column or row is cropped.
    alto, ancho = imagenes[0].shape[:2]
    alto, ancho = alto - alto % 2, ancho - ancho % 2
    tasa = Fraction(fps).limit_denominator(1000)
    descriptor, nombre = tempfile.mkstemp(prefix=_PREFIJO_TEMPORAL, suffix=".mp4", dir=directorio)
    os.close(descriptor)
    ruta = Path(nombre)
    try:
        with av.open(str(ruta), mode="w", format="mp4", options=_FASTSTART) as mp4:
            flujo = mp4.add_stream("libx264", rate=tasa)
            contexto = flujo.codec_context
            contexto.pix_fmt = "yuv420p"
            contexto.width, contexto.height = ancho, alto
            contexto.time_base = 1 / tasa
            contexto.gop_size = max(1, round(fps * GOP_S))
            contexto.max_b_frames = 0
            # Keyframes only on the GOP, at fixed positions.
            contexto.options = {"profile": PERFIL, "sc_threshold": "0"}
            for indice, imagen in enumerate(imagenes):
                cuadro = av.VideoFrame.from_ndarray(imagen, format="bgr24")
                if (imagen.shape[1], imagen.shape[0]) != (ancho, alto):
                    cuadro = cuadro.reformat(width=ancho, height=alto)
                cuadro.pts = indice  # constant frame rate: one tick of 1/fps per frame
                mp4.mux(flujo.encode(cuadro))
            mp4.mux(flujo.encode(None))
        return ruta.read_bytes()
    except (av.error.FFmpegError, ValueError, OSError) as error:
        raise ErrorCodificacionError(f"No se pudo codificar el clip: {error}") from error
    finally:
        ruta.unlink(missing_ok=True)


def _decodificar(jpeg: bytes) -> npt.NDArray[np.uint8]:
    imagen = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
    if imagen is None:
        raise ErrorCodificacionError("Un fotograma del clip no es un JPEG válido")
    return np.ascontiguousarray(imagen, dtype=np.uint8)
