"""Parámetros cinemáticos que se calculan en cada fotograma a partir de los landmarks.

Son funciones puras: no leen la cámara, la red ni el reloj, así que se prueban con poses
sintéticas o grabadas. Cada función indica la regla que implementa; las fórmulas completas,
sus fuentes y las adaptaciones están en ``docs/especificacion-clasificacion.md``.

Antes de calcular, todo se pasa a píxeles (adaptación A1), porque MediaPipe normaliza ``x`` por
el ancho e ``y`` por el alto, y en una imagen 640 × 480 eso deforma ángulos y proporciones.
"""

import math
from dataclasses import dataclass

from detection_worker.pose.schemas import Indice, Pose, Punto


@dataclass(frozen=True, slots=True)
class Parametros:
    """Parámetros de un fotograma."""

    centro_cadera: Punto
    longitud_linea_central: float
    angulo_grados: float
    razon_ancho_alto: float


def punto_medio(a: Punto, b: Punto) -> Punto:
    return Punto((a.x + b.x) / 2, (a.y + b.y) / 2)


def centro_cadera(pose: Pose) -> Punto:
    """Punto medio entre las dos caderas (regla R1).

    Representa el centro de gravedad del cuerpo: cuando alguien cae, es el punto que baja de
    forma brusca.
    """
    return punto_medio(
        pose.en_pixeles(Indice.CADERA_DERECHA), pose.en_pixeles(Indice.CADERA_IZQUIERDA)
    )


def extremos_linea_central(pose: Pose) -> tuple[Punto, Punto]:
    """Extremos de la línea central del cuerpo: la cabeza y el punto medio de los tobillos (R2).

    MediaPipe no tiene un punto «cabeza», así que se usa la nariz (adaptación A2).
    """
    cabeza = pose.en_pixeles(Indice.NARIZ)
    pies = punto_medio(
        pose.en_pixeles(Indice.TOBILLO_DERECHO), pose.en_pixeles(Indice.TOBILLO_IZQUIERDO)
    )
    return cabeza, pies


def angulo_linea_central(pose: Pose) -> float:
    """Ángulo entre la línea central y el suelo, en grados (R2).

    90° es una persona de pie y 0° una persona tendida. Al caer, el cuerpo pierde la vertical y
    el ángulo baja. Se calcula con ``atan2`` sobre las diferencias absolutas, que equivale a
    arctan(|Δy| / |Δx|) pero no falla cuando la persona está totalmente vertical (Δx = 0).
    """
    cabeza, pies = extremos_linea_central(pose)
    return math.degrees(math.atan2(abs(cabeza.y - pies.y), abs(cabeza.x - pies.x)))


def longitud_linea_central(pose: Pose) -> float:
    """Largo de la línea central en píxeles; sirve de escala para la velocidad (adaptación A3)."""
    cabeza, pies = extremos_linea_central(pose)
    return math.hypot(cabeza.x - pies.x, cabeza.y - pies.y)


def razon_ancho_alto(pose: Pose, visibilidad_min: float) -> float:
    """Ancho dividido entre alto del rectángulo que encierra el cuerpo (R3).

    De pie el rectángulo es angosto y alto (razón < 1); tendido en el suelo es ancho y bajo
    (razón > 1). Solo se usan los landmarks suficientemente visibles (adaptación A5). Si el
    rectángulo no tiene altura, el cuerpo está totalmente horizontal y se devuelve infinito.
    """
    puntos = pose.visibles(visibilidad_min)
    if len(puntos) < 2:
        raise ValueError("Se necesitan al menos dos landmarks visibles")
    ancho = max(p.x for p in puntos) - min(p.x for p in puntos)
    alto = max(p.y for p in puntos) - min(p.y for p in puntos)
    return math.inf if alto == 0 else ancho / alto


def velocidad_descenso(y1: float, y2: float, dt: float, escala: float) -> float:
    """Velocidad vertical del centro de la cadera entre dos instantes (R1).

    Se usa el valor absoluto del desplazamiento vertical dividido entre el tiempo. Una sola
    cámara no mide metros, así que el resultado se divide además entre el largo de la línea
    central: la unidad queda en «cuerpos por segundo» y no cambia si la persona está cerca o
    lejos de la cámara (adaptación A3).
    """
    if dt <= 0:
        raise ValueError("Δt debe ser positivo")
    if escala <= 0:
        raise ValueError("La escala debe ser positiva")
    return abs(y2 - y1) / dt / escala


def calcular(pose: Pose, visibilidad_min: float) -> Parametros:
    """Calcula los parámetros de un fotograma."""
    return Parametros(
        centro_cadera=centro_cadera(pose),
        longitud_linea_central=longitud_linea_central(pose),
        angulo_grados=angulo_linea_central(pose),
        razon_ancho_alto=razon_ancho_alto(pose, visibilidad_min),
    )
