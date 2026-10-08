"""H.264 publisher of the live view (PyAV), to the ``urlPublicacion`` the API sends.

The API decides the URL (``rtsp://…`` locally, ``rtsps://…`` in production); the agent opens
whatever it gets. RTSP goes over TCP. The publish user and token go in the URL's userinfo,
percent-encoded, which is how FFmpeg's RTSP client sends credentials; the URL is never logged.

Encoder settings (implementation choice, low latency): ``libx264`` with the ``veryfast`` preset
and ``zerolatency`` tune (no B-frames, no lookahead), one keyframe per second (``GOP_S``) so a
new viewer starts within a second, about 8 fps from the capture loop and no audio.
"""

import logging
from fractions import Fraction
from typing import Any, Protocol
from urllib.parse import quote, urlsplit, urlunsplit

from te_tengo_captura.captura.fuentes import FPS, Imagen

logger = logging.getLogger(__name__)

GOP_S = 1.0
TASA_BITS = 1_000_000
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


class PublicadorPyAV:
    """One publishing connection. It connects on the first picture (when its size is known)."""

    def __init__(self, url: str, fps: float = FPS) -> None:
        self._url = url
        self._fps = fps
        self._contenedor: Any = None
        self._flujo: Any = None
        self._inicio: float | None = None
        self._ultimo_pts = -1

    def publicar(self, imagen: Imagen, instante: float) -> None:
        import av

        if self._contenedor is None:
            self._abrir(imagen)
        if self._inicio is None:
            self._inicio = instante
        pts = max(self._ultimo_pts + 1, round((instante - self._inicio) * 1000))
        self._ultimo_pts = pts
        cuadro = av.VideoFrame.from_ndarray(imagen, format="bgr24")
        cuadro.pts = pts
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
            flujo.width = imagen.shape[1]
            flujo.height = imagen.shape[0]
            flujo.pix_fmt = "yuv420p"
            flujo.bit_rate = TASA_BITS
            flujo.codec_context.time_base = BASE_TIEMPO
            flujo.codec_context.gop_size = max(1, round(self._fps * GOP_S))
            flujo.codec_context.max_b_frames = 0
            flujo.codec_context.options = {
                "preset": "veryfast",
                "tune": "zerolatency",
                "profile": "main",
            }
        except Exception:
            contenedor.close()
            raise
        self._contenedor, self._flujo = contenedor, flujo
