"""Per-frame measurement: parameters (R1 to R3) and hip descent speed.

It is kept separate from the state machine so that measuring is possible without classifying;
for example, to watch the values live with the camera while the thresholds are calibrated.
"""

import statistics
from collections import deque
from dataclasses import dataclass

from detection_worker.clasificacion import parametros
from detection_worker.pose.schemas import Pose


@dataclass(frozen=True, slots=True)
class Medicion:
    instante: float
    parametros: parametros.Parametros
    velocidad: float | None  # None if the frame cannot be used to measure it


@dataclass(frozen=True, slots=True)
class _Muestra:
    instante: float
    y_cadera: float
    largo: float


class MedidorCinematico:
    """Computes the parameters of each frame and the hip descent speed (R1).

    The speed is the largest drop per second between the current frame and each frame in the
    preceding window (from ``ventana_s`` back to ``separacion_min_s`` back). This tolerates the
    frames that MediaPipe loses right during the fall (adaptation A3). Only frames with the key
    points visible are used (A6): with doubtful points the hip "jumps" and produces impossible
    speeds. The scale is the median length of the center line over the last few seconds, which
    is more stable than that of a single frame.
    """

    def __init__(self, separacion_min_s: float, ventana_s: float, visibilidad_min: float) -> None:
        self._separacion = separacion_min_s
        self._ventana = ventana_s
        self._visibilidad_min = visibilidad_min
        self._historial: deque[_Muestra] = deque()

    def medir(self, instante: float, pose: Pose) -> Medicion:
        p = parametros.calcular(pose, self._visibilidad_min)
        if not p.puntos_visibles:
            return Medicion(instante, p, None)
        velocidad = self._velocidad(instante, p)
        self._historial.append(_Muestra(instante, p.centro_cadera.y, p.longitud_linea_central))
        while self._historial and self._historial[0].instante < instante - 2 * self._ventana:
            self._historial.popleft()
        return Medicion(instante, p, velocidad)

    def _velocidad(self, instante: float, p: parametros.Parametros) -> float | None:
        anteriores = [
            m
            for m in self._historial
            if instante - self._ventana <= m.instante <= instante - self._separacion
        ]
        largos = [m.largo for m in self._historial if m.largo > 0]
        if not anteriores or not largos:
            return None
        escala = statistics.median(largos)
        return max(
            parametros.velocidad_descenso(
                m.y_cadera, p.centro_cadera.y, instante - m.instante, escala
            )
            for m in anteriores
        )
