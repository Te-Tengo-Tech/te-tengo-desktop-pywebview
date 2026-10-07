"""Kinematic parameters computed on every frame from the landmarks.

They are pure functions: they do not read the camera, the network or the clock, so they are
tested with synthetic or recorded poses. Each function states the rule it implements; the full
formulas, their sources and the adaptations are in ``docs/classification-spec.md``.

Before computing, everything is converted to pixels (adaptation A1), because MediaPipe
normalizes ``x`` by the width and ``y`` by the height, and in a 640 × 480 image that distorts
angles and proportions.
"""

import math
from dataclasses import dataclass

from te_tengo_deteccion.pose.schemas import Indice, Pose, Punto


@dataclass(frozen=True, slots=True)
class Parametros:
    """Parameters of one frame."""

    centro_cadera: Punto
    longitud_linea_central: float
    angulo_grados: float
    razon_ancho_alto: float
    cabeza_bajo_pies: bool
    puntos_visibles: bool


# Landmarks used by the formulas: nose, hips and ankles.
PUNTOS_CLAVE = (
    Indice.NARIZ,
    Indice.CADERA_IZQUIERDA,
    Indice.CADERA_DERECHA,
    Indice.TOBILLO_IZQUIERDO,
    Indice.TOBILLO_DERECHO,
)


def puntos_clave_visibles(pose: Pose, visibilidad_min: float) -> bool:
    """Tells whether the points used by the formulas are clearly visible (adaptation A6).

    If any of them is not clearly visible, MediaPipe still returns an estimated position, but an
    unreliable one: with it, a lying person cut off by the edge of the image can look like they
    are standing. That is why such poses cannot declare that the person got up.
    """
    return all(pose.landmarks[i].visibilidad >= visibilidad_min for i in PUNTOS_CLAVE)


def punto_medio(a: Punto, b: Punto) -> Punto:
    return Punto((a.x + b.x) / 2, (a.y + b.y) / 2)


def centro_cadera(pose: Pose) -> Punto:
    """Midpoint between the two hips (rule R1).

    It represents the body's center of gravity: when someone falls, it is the point that drops
    sharply.
    """
    return punto_medio(
        pose.en_pixeles(Indice.CADERA_DERECHA), pose.en_pixeles(Indice.CADERA_IZQUIERDA)
    )


def extremos_linea_central(pose: Pose) -> tuple[Punto, Punto]:
    """Ends of the body's center line: the head and the midpoint of the ankles (R2).

    MediaPipe has no "head" point, so the nose is used (adaptation A2).
    """
    cabeza = pose.en_pixeles(Indice.NARIZ)
    pies = punto_medio(
        pose.en_pixeles(Indice.TOBILLO_DERECHO), pose.en_pixeles(Indice.TOBILLO_IZQUIERDO)
    )
    return cabeza, pies


def angulo_linea_central(pose: Pose) -> float:
    """Angle between the center line and the floor, in degrees (R2).

    90° is a standing person and 0° a lying person. When falling, the body loses its vertical
    alignment and the angle drops. It is computed with ``atan2`` on the absolute differences,
    which is equivalent to arctan(|Δy| / |Δx|) but does not fail when the person is fully
    vertical (Δx = 0).
    """
    cabeza, pies = extremos_linea_central(pose)
    return math.degrees(math.atan2(abs(cabeza.y - pies.y), abs(cabeza.x - pies.x)))


def cabeza_bajo_pies(pose: Pose) -> bool:
    """Tells whether the head ended up lower than the feet in the image (adaptation A7).

    A standing person always has the head above the feet. If they fall towards the camera, the
    body appears foreshortened: the absolute-value angle comes out "almost vertical" and the
    width/height ratio does not exceed 1, but the head ends up below the feet. This signal
    detects that case.
    """
    cabeza, pies = extremos_linea_central(pose)
    return cabeza.y > pies.y


def longitud_linea_central(pose: Pose) -> float:
    """Length of the center line in pixels; used as the scale for the speed (adaptation A3)."""
    cabeza, pies = extremos_linea_central(pose)
    return math.hypot(cabeza.x - pies.x, cabeza.y - pies.y)


def razon_ancho_alto(pose: Pose, visibilidad_min: float) -> float:
    """Width divided by height of the rectangle that encloses the body (R3).

    When standing, the rectangle is narrow and tall (ratio < 1); when lying on the floor, it is
    wide and low (ratio > 1). Only sufficiently visible landmarks are used (adaptation A5). If
    the rectangle has no height, the body is fully horizontal and infinity is returned.
    """
    puntos = pose.visibles(visibilidad_min)
    if len(puntos) < 2:
        raise ValueError("Se necesitan al menos dos landmarks visibles")
    ancho = max(p.x for p in puntos) - min(p.x for p in puntos)
    alto = max(p.y for p in puntos) - min(p.y for p in puntos)
    return math.inf if alto == 0 else ancho / alto


def velocidad_descenso(y1: float, y2: float, dt: float, escala: float) -> float:
    """Speed at which the hip center drops between two instants (R1).

    It is positive when the hip drops and negative when it rises (adaptation A3): this way,
    getting up quickly is not mistaken for falling. A single camera does not measure meters, so
    the value is divided by the length of the center line and the unit becomes "bodies per
    second", independent of the distance to the camera.
    """
    if dt <= 0:
        raise ValueError("Δt debe ser positivo")
    if escala <= 0:
        raise ValueError("La escala debe ser positiva")
    return (y2 - y1) / dt / escala


def calcular(pose: Pose, visibilidad_min: float) -> Parametros:
    """Computes the parameters of one frame."""
    return Parametros(
        centro_cadera=centro_cadera(pose),
        longitud_linea_central=longitud_linea_central(pose),
        angulo_grados=angulo_linea_central(pose),
        razon_ancho_alto=razon_ancho_alto(pose, visibilidad_min),
        cabeza_bajo_pies=cabeza_bajo_pies(pose),
        puntos_visibles=puntos_clave_visibles(pose, visibilidad_min),
    )
