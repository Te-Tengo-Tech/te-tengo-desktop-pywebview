"""Parámetros cinemáticos de Chen et al. (2020) calculados sobre landmarks de MediaPipe.

Funciones puras: no leen la cámara, la red ni el reloj. Así se prueban con secuencias de
landmarks grabadas o sintéticas.

Fuente: Chen, W., Jiang, Z., Guo, H., & Ni, X. (2020). Fall detection based on key points of
human-skeleton using OpenPose. *Symmetry, 12*(5), 744. https://doi.org/10.3390/sym12050744

Correspondencia de puntos (Chen, Figura 4 → MediaPipe):
    s0 cabeza → 0 nariz · s8/s11 caderas → 24/23 · s10/s13 tobillos → 28/27
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
    """Centro de la articulación de la cadera: (s8 + s11) / 2 (Chen, sección 3.2, ec. 1)."""
    return punto_medio(
        pose.en_pixeles(Indice.CADERA_DERECHA), pose.en_pixeles(Indice.CADERA_IZQUIERDA)
    )


def extremos_linea_central(pose: Pose) -> tuple[Punto, Punto]:
    """Extremos de la línea central L: cabeza s0 y punto medio de los tobillos (s10 + s13) / 2.

    Chen (sección 3.3, ec. 4). MediaPipe no tiene un punto «cabeza»; se usa la nariz.
    """
    cabeza = pose.en_pixeles(Indice.NARIZ)
    pies = punto_medio(
        pose.en_pixeles(Indice.TOBILLO_DERECHO), pose.en_pixeles(Indice.TOBILLO_IZQUIERDO)
    )
    return cabeza, pies


def angulo_linea_central(pose: Pose) -> float:
    """Ángulo θ entre la línea central y el suelo, en grados (0° tendido, 90° de pie).

    Chen: θ = arctan |(y0 − ȳ) / (x0 − x̄)|. Se calcula con ``atan2`` para no dividir entre cero
    cuando la persona está totalmente vertical (x0 = x̄).
    """
    cabeza, pies = extremos_linea_central(pose)
    return math.degrees(math.atan2(abs(cabeza.y - pies.y), abs(cabeza.x - pies.x)))


def longitud_linea_central(pose: Pose) -> float:
    """Longitud de L en píxeles: escala para normalizar la velocidad (adaptación propia)."""
    cabeza, pies = extremos_linea_central(pose)
    return math.hypot(cabeza.x - pies.x, cabeza.y - pies.y)


def razon_ancho_alto(pose: Pose, visibilidad_min: float) -> float:
    """P = ancho / alto del rectángulo que encierra el cuerpo (Chen, sección 3.4, ec. 5).

    El rectángulo se arma con los landmarks visibles, en píxeles. Si no hay altura, devuelve
    infinito (cuerpo completamente horizontal).
    """
    puntos = pose.visibles(visibilidad_min)
    if len(puntos) < 2:
        raise ValueError("Se necesitan al menos dos landmarks visibles")
    ancho = max(p.x for p in puntos) - min(p.x for p in puntos)
    alto = max(p.y for p in puntos) - min(p.y for p in puntos)
    return math.inf if alto == 0 else ancho / alto


def velocidad_descenso(y1: float, y2: float, dt: float, escala: float) -> float:
    """Velocidad del centro de la cadera: v = |y(t2) − y(t1)| / Δt (Chen, sección 3.2, ec. 2).

    Chen la expresa en m/s, que una sola cámara 2D no puede medir. Adaptación propia: se divide
    entre la longitud de la línea central para que el valor no dependa de la distancia a la
    cámara. Unidad resultante: longitudes de línea central por segundo.
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
