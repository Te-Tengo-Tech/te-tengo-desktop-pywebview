"""Tipos de datos de la estimación de pose.

MediaPipe Pose Landmarker entrega 33 landmarks por persona. Sus coordenadas ``x`` e ``y`` van
de 0 a 1 (divididas entre el ancho y el alto de la imagen) e ``y`` crece hacia abajo. Detalle y
fuente en ``docs/especificacion-clasificacion.md`` (sección 1).
"""

from dataclasses import dataclass
from enum import IntEnum


class Indice(IntEnum):
    """Índices de MediaPipe usados por la clasificación cinemática."""

    NARIZ = 0
    HOMBRO_IZQUIERDO = 11
    HOMBRO_DERECHO = 12
    CADERA_IZQUIERDA = 23
    CADERA_DERECHA = 24
    RODILLA_IZQUIERDA = 25
    RODILLA_DERECHA = 26
    TOBILLO_IZQUIERDO = 27
    TOBILLO_DERECHO = 28


TOTAL_LANDMARKS = 33


@dataclass(frozen=True, slots=True)
class Punto:
    """Punto en píxeles de la imagen (``y`` crece hacia abajo)."""

    x: float
    y: float


@dataclass(frozen=True, slots=True)
class Landmark:
    """Landmark normalizado (0-1) con su probabilidad de estar visible."""

    x: float
    y: float
    visibilidad: float


@dataclass(frozen=True, slots=True)
class Pose:
    """Pose de una persona en un fotograma, con el tamaño de la imagen en píxeles."""

    landmarks: tuple[Landmark, ...]
    ancho: int
    alto: int

    def __post_init__(self) -> None:
        if len(self.landmarks) != TOTAL_LANDMARKS:
            raise ValueError(
                f"Se esperaban {TOTAL_LANDMARKS} landmarks y llegaron {len(self.landmarks)}"
            )
        if self.ancho <= 0 or self.alto <= 0:
            raise ValueError("El tamaño de la imagen debe ser positivo")

    def en_pixeles(self, indice: int) -> Punto:
        """Convierte un landmark normalizado a píxeles.

        Hace falta porque MediaPipe normaliza ``x`` por el ancho e ``y`` por el alto: sin esta
        conversión, distancias y proporciones salen deformadas cuando la imagen no es cuadrada.
        """
        lm = self.landmarks[indice]
        return Punto(lm.x * self.ancho, lm.y * self.alto)

    def visibles(self, visibilidad_min: float) -> list[Punto]:
        """Landmarks en píxeles cuya visibilidad alcanza el mínimo."""
        return [
            Punto(lm.x * self.ancho, lm.y * self.alto)
            for lm in self.landmarks
            if lm.visibilidad >= visibilidad_min
        ]
