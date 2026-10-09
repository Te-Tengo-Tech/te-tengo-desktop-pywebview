"""H.264 publisher of the live view (PyAV), to the ``urlPublicacion`` the API sends.

The API decides the URL (``rtsp://…`` locally, ``rtsps://…`` in production); the agent opens
whatever it gets. RTSP goes over TCP. The publish user and token go in the URL's userinfo,
percent-encoded, which is how FFmpeg's RTSP client sends credentials; the URL is never logged.

Encoder settings (implementation choices, low latency and playable over WebRTC in every
browser): ``libx264`` with the ``veryfast`` preset, the ``zerolatency`` tune (no lookahead) and
the **Constrained Baseline** profile (no B-frames, no CABAC); one keyframe every half second
(``GOP_S``, no extra keyframes on scene changes), so a new viewer starts within half a
second; about ``TASA_BITS`` with a capped peak (``TASA_MAXIMA``, ``BUFER_BITS``) so keyframes
do not burst; no audio. Every publication has its own encoder, so its first frame is always a
keyframe.

Timestamps follow a constant frame rate, not the capture clock's jitter: each frame goes to the
nearest slot of a ``1/fps`` grid counted from the publication's first frame (the live view
already hands over frames numbered on that grid, ``en_vivo.Ritmo``). A webcam's real intervals
jitter by a few milliseconds and Apple's low-latency HLS player rejects a stream whose parts
change duration (MediaMTX warns "part duration changed … this will cause an error in iOS
clients"); a frame the webcam did not deliver leaves its slot empty instead of slowing the clock
down.
"""

import logging
from fractions import Fraction
from typing import Any, Protocol
from urllib.parse import quote, urlsplit, urlunsplit

from te_tengo_captura.captura.fuentes import Imagen

logger = logging.getLogger(__name__)

FPS_VIVO = 15.0
GOP_S = 0.5
TASA_BITS = 1_000_000
TASA_MAXIMA = 1_500_000
BUFER_BITS = 1_000_000
PERFIL = "baseline"  # libx264 only produces Constrained Baseline for it
TIMEOUT_US = 5_000_000  # socket I/O timeout of FFmpeg's RTSP client, in microseconds
BASE_TIEMPO = Fraction(1, 1000)  # frame timestamps in milliseconds


class Publicador(Protocol):
    def publicar(self, imagen: Imagen, instante: float) -> None:
        """Encodes and sends one BGR picture; raises if the connection fails."""
        ...

    def cerrar(self) -> None: ...


def url_con_credenciales(url: str, usuario: str | None, clave: str | None) -> str:
    """``rtsp://usuario:clave@host:puerto/ruta`` with both parts percent-encoded."""
    if not usuario:
        return url
    partes = urlsplit(url)
    host = partes.hostname or ""
    if ":" in host:  # IPv6 literal
        host = f"[{host}]"
    if partes.port is not None:
        host = f"{host}:{partes.port}"
    userinfo = quote(usuario, safe="") + (f":{quote(clave, safe='')}" if clave else "")
    return urlunsplit(partes._replace(netloc=f"{userinfo}@{host}"))


def _configurar(contexto: Any, ancho: int, alto: int, fps: float) -> None:
    """The live view's encoder settings on a PyAV video codec context (see the module doc)."""
    contexto.width = ancho
    contexto.height = alto
    contexto.pix_fmt = "yuv420p"
    contexto.bit_rate = TASA_BITS
    contexto.time_base = BASE_TIEMPO
    contexto.framerate = Fraction(round(fps * 1000), 1000)
    contexto.gop_size = max(1, round(fps * GOP_S))
    contexto.max_b_frames = 0
    contexto.options = {
        "preset": "veryfast",
        "tune": "zerolatency",
        "profile": PERFIL,
        # Keyframes only on the GOP: without weighted prediction (not in Baseline) a change of
        # light would otherwise make every frame a keyframe, a burst nobody needs at 0.5 s GOP.
        "sc_threshold": "0",
        "maxrate": str(TASA_MAXIMA),
        "bufsize": str(BUFER_BITS),
    }


def calentar_codificador(ancho: int, alto: int, fps: float = FPS_VIVO) -> None:
    """Loads PyAV, FFmpeg and libx264 and runs the encoder once on a plain grey picture.

    Pre-warm (``preparar``): the first ``import av`` and the first encoder of a process are the
    slow ones. Nothing is sent and no camera pixel is used; the encoder is thrown away.
    """
    import av
    import numpy as np

    contexto: Any = av.CodecContext.create("libx264", "w")
    _configurar(contexto, ancho, alto, fps)
    contexto.open()
    cuadro = av.VideoFrame.from_ndarray(np.full((alto, ancho, 3), 128, np.uint8), format="bgr24")
    cuadro.pts = 0
    cuadro.time_base = BASE_TIEMPO
    contexto.encode(cuadro)
    contexto.encode(None)


class PublicadorPyAV:
    """One publication. It connects on the first picture (when its size is known)."""

    def __init__(self, url: str, fps: float = FPS_VIVO) -> None:
        self._url = url
        self._fps = fps
        self._contenedor: Any = None
        self._flujo: Any = None
        self._inicio: float | None = None
        self._ultimo_cuadro = -1

    def publicar(self, imagen: Imagen, instante: float) -> None:
        import av

        if self._contenedor is None:
            self._abrir(imagen)
        if self._inicio is None:
            self._inicio = instante
        # Never repeat or go back in time, even if the source's clock does.
        numero = max(self._ultimo_cuadro + 1, round((instante - self._inicio) * self._fps))
        self._ultimo_cuadro = numero
        cuadro = av.VideoFrame.from_ndarray(imagen, format="bgr24")
        cuadro.pts = round(numero * 1000 / self._fps)
        cuadro.time_base = BASE_TIEMPO
        for paquete in self._flujo.encode(cuadro):
            self._contenedor.mux(paquete)

    def cerrar(self) -> None:
        contenedor, self._contenedor = self._contenedor, None
        if contenedor is None:
            return
        try:
            for paquete in self._flujo.encode(None):
                contenedor.mux(paquete)
        except Exception as error:  # the server may already be gone
            logger.debug("Vista en vivo: no se pudo vaciar el codificador: %s", error)
        finally:
            try:
                contenedor.close()
            except Exception as error:
                logger.debug("Vista en vivo: cierre con error: %s", error)

    def _abrir(self, imagen: Imagen) -> None:
        import av

        esquema = urlsplit(self._url).scheme.lower()
        rtsp = esquema in ("rtsp", "rtsps")
        opciones = {"rtsp_transport": "tcp", "timeout": str(TIMEOUT_US)} if rtsp else {}
        contenedor = av.open(self._url, mode="w", format="rtsp" if rtsp else None, options=opciones)
        try:
            flujo = contenedor.add_stream("libx264", rate=round(self._fps))
            _configurar(flujo.codec_context, imagen.shape[1], imagen.shape[0], self._fps)
        except Exception:
            contenedor.close()
            raise
        self._contenedor, self._flujo = contenedor, flujo
