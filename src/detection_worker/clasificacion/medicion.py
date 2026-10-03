"""Medición por fotograma: parámetros (R1 a R3) y velocidad, con el historial que esta necesita.

Está separada de la máquina de estados para poder medir sin clasificar; por ejemplo, para ver
los valores en vivo con la cámara mientras se calibra el umbral de velocidad.
"""

from collections import deque
from dataclasses import dataclass

from detection_worker.clasificacion import parametros
from detection_worker.pose.schemas import Pose


@dataclass(frozen=True, slots=True)
class Medicion:
    instante: float
    parametros: parametros.Parametros
    velocidad: float | None  # None mientras no haya una muestra anterior a la distancia mínima


@dataclass(frozen=True, slots=True)
class _Muestra:
    instante: float
    y_cadera: float
    escala: float


class MedidorCinematico:
    """Calcula los parámetros de cada fotograma y la velocidad de bajada de la cadera (R1).

    La velocidad se mide contra la muestra más reciente que esté al menos ``intervalo_s`` antes,
    usando como escala el largo de la línea central de esa muestra anterior (adaptación A3).
    """

    def __init__(self, intervalo_s: float, visibilidad_min: float) -> None:
        self._intervalo = intervalo_s
        self._visibilidad_min = visibilidad_min
        self._historial: deque[_Muestra] = deque()

    def medir(self, instante: float, pose: Pose) -> Medicion:
        p = parametros.calcular(pose, self._visibilidad_min)
        velocidad = self._velocidad(instante, p)
        self._registrar(instante, p)
        return Medicion(instante, p, velocidad)

    def _velocidad(self, instante: float, p: parametros.Parametros) -> float | None:
        limite = instante - self._intervalo
        for muestra in reversed(self._historial):
            if muestra.instante <= limite:
                return parametros.velocidad_descenso(
                    muestra.y_cadera, p.centro_cadera.y, instante - muestra.instante, muestra.escala
                )
        return None

    def _registrar(self, instante: float, p: parametros.Parametros) -> None:
        if p.longitud_linea_central > 0:
            self._historial.append(_Muestra(instante, p.centro_cadera.y, p.longitud_linea_central))
        antiguedad_max = 4 * self._intervalo
        while self._historial and self._historial[0].instante < instante - antiguedad_max:
            self._historial.popleft()
