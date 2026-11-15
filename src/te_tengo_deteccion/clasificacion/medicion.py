"""Per-frame measurement: parameters (R1 to R3) and hip descent speed.

It is kept separate from the state machine so that measuring is possible without classifying;
for example, to watch the values live with the camera while the thresholds are calibrated.
"""

import math
import statistics
from collections import deque
from dataclasses import dataclass

from te_tengo_deteccion.clasificacion import parametros
from te_tengo_deteccion.pose.schemas import Pose, Punto


@dataclass(frozen=True, slots=True)
class Medicion:
    instante: float
    parametros: parametros.Parametros
    velocidad: float | None  # None if the frame cannot be used to measure it
    sin_tobillos: bool = False  # S3: the speed was measured with the upper body
    salto: bool = False  # S4: the hip jumped too far since the last pose (another person)


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

    Two optional proposals (ADR 0012, off by default) extend it:

    * ``sin_tobillos`` (S3): a frame that fails A6 but has the nose, the shoulders and the hips
      visible gets a speed measured on a separate history of such upper-body frames, scaled
      with the length estimated from the nose and the hips (the ankles are not used).
    * ``salto_max`` (S4): when the hip center moves more than this many center-line lengths
      between two consecutive poses less than 0.5 s apart, the pose belongs to someone else
      (the model switched person): the histories are cleared and the measurement says so.
    """

    def __init__(
        self,
        separacion_min_s: float,
        ventana_s: float,
        visibilidad_min: float,
        sin_tobillos: bool = False,
        salto_max: float | None = None,
    ) -> None:
        self._separacion = separacion_min_s
        self._ventana = ventana_s
        self._visibilidad_min = visibilidad_min
        self._sin_tobillos = sin_tobillos
        self._salto_max = salto_max
        self._historial: deque[_Muestra] = deque()
        self._historial_tronco: deque[_Muestra] = deque()
        self._previa: tuple[float, Punto, float] | None = None

    def reiniciar(self) -> None:
        """Forgets the speed histories (S4: the pose now belongs to another person)."""
        self._historial.clear()
        self._historial_tronco.clear()

    def medir(self, instante: float, pose: Pose) -> Medicion:
        p = parametros.calcular(pose, self._visibilidad_min)
        salto = self._salto(instante, p)
        if salto:
            self.reiniciar()
        velocidad_tronco: float | None = None
        if self._sin_tobillos and p.tronco_visible and p.largo_estimado > 0:
            velocidad_tronco = self._velocidad(instante, p, self._historial_tronco)
            self._agregar(
                self._historial_tronco, _Muestra(instante, p.centro_cadera.y, p.largo_estimado)
            )
        if not p.puntos_visibles:
            if velocidad_tronco is not None:
                return Medicion(instante, p, velocidad_tronco, sin_tobillos=True, salto=salto)
            return Medicion(instante, p, None, salto=salto)
        velocidad = self._velocidad(instante, p, self._historial)
        self._agregar(
            self._historial, _Muestra(instante, p.centro_cadera.y, p.longitud_linea_central)
        )
        return Medicion(instante, p, velocidad, salto=salto)

    def _agregar(self, historial: deque[_Muestra], muestra: _Muestra) -> None:
        historial.append(muestra)
        while historial and historial[0].instante < muestra.instante - 2 * self._ventana:
            historial.popleft()

    def _salto(self, instante: float, p: parametros.Parametros) -> bool:
        """S4: whether the hip center jumped farther than a person can move between poses."""
        if self._salto_max is None:
            return False
        previa = self._previa
        self._previa = (instante, p.centro_cadera, p.longitud_linea_central)
        if previa is None or instante - previa[0] > 0.5:
            return False
        largos = [m.largo for m in self._historial if m.largo > 0]
        escala = statistics.median(largos) if largos else max(previa[2], p.longitud_linea_central)
        if escala <= 0:
            return False
        distancia = math.hypot(p.centro_cadera.x - previa[1].x, p.centro_cadera.y - previa[1].y)
        return distancia / escala > self._salto_max

    def _velocidad(
        self, instante: float, p: parametros.Parametros, historial: deque[_Muestra]
    ) -> float | None:
        anteriores = [
            m
            for m in historial
            if instante - self._ventana <= m.instante <= instante - self._separacion
        ]
        largos = [m.largo for m in historial if m.largo > 0]
        if not anteriores or not largos:
            return None
        escala = statistics.median(largos)
        return max(
            parametros.velocidad_descenso(
                m.y_cadera, p.centro_cadera.y, instante - m.instante, escala
            )
            for m in anteriores
        )
