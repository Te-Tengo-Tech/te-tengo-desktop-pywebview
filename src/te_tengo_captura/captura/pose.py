"""Synchronous MediaPipe pose estimator for the capture worker thread.

ADR 0006: VIDEO mode with one tracker for the webcam, fed with increasing millisecond
timestamps. In the desktop agent MediaPipe runs in the capture worker thread (AGENTS.md,
"Threads"); the separate process of ADR 0003 belonged to the retired server.
"""

from pathlib import Path
from typing import Any, Protocol

from te_tengo_captura.captura.fuentes import Imagen
from te_tengo_deteccion.pose.schemas import Pose
from te_tengo_deteccion.pose.service import crear_landmarker, detectar


class Estimador(Protocol):
    def estimar(self, imagen: Imagen, instante_ms: int) -> Pose | None: ...

    def reiniciar(self) -> None:
        """Drops the tracking state (after a pause or when timestamps go back)."""
        ...

    def cerrar(self) -> None: ...


class EstimadorMediaPipe:
    def __init__(self, ruta_modelo: Path, confianza_min: float = 0.5) -> None:
        if not ruta_modelo.is_file():
            raise FileNotFoundError(
                f"No existe el modelo {ruta_modelo}. Descárgalo con: make modelo"
            )
        self._ruta = str(ruta_modelo)
        self._confianza = confianza_min
        self._landmarker: Any = None
        self._ultimo_ms = -1

    def estimar(self, imagen: Imagen, instante_ms: int) -> Pose | None:
        if self._landmarker is None or instante_ms <= self._ultimo_ms:
            self.reiniciar()
            self._landmarker = crear_landmarker(self._ruta, self._confianza, modo="video")
        self._ultimo_ms = instante_ms
        return detectar(self._landmarker, imagen, instante_ms)

    def reiniciar(self) -> None:
        if self._landmarker is not None:
            self._landmarker.close()
        self._landmarker = None
        self._ultimo_ms = -1

    def cerrar(self) -> None:
        self.reiniciar()
