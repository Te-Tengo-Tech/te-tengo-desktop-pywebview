"""Medición por fotograma: parámetros (R1 a R3) y velocidad de bajada de la cadera.

Está separada de la máquina de estados para poder medir sin clasificar; por ejemplo, para ver
los valores en vivo con la cámara mientras se calibran los umbrales.
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
    velocidad: float | None  # None si el fotograma no sirve para medirla


@dataclass(frozen=True, slots=True)
class _Muestra:
    instante: float
    y_cadera: float
    largo: float


class MedidorCinematico:
    """Calcula los parámetros de cada fotograma y la velocidad de bajada de la cadera (R1).

    La velocidad es la mayor bajada por segundo entre el fotograma actual y cada fotograma de la
    ventana anterior (de ``ventana_s`` hasta ``separacion_min_s`` atrás). Así tolera los
    fotogramas que MediaPipe pierde justo durante la caída (adaptación A3). Solo se usan
    fotogramas con los puntos clave visibles (A6): con puntos dudosos la cadera «salta» y genera
    velocidades imposibles. La escala es la mediana del largo de la línea central de los últimos
    segundos, más estable que el de un solo fotograma.
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
