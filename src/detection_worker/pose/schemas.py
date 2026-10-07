"""Data types of the pose estimation.

MediaPipe Pose Landmarker returns 33 landmarks per person. Their ``x`` and ``y`` coordinates
range from 0 to 1 (divided by the image width and height) and ``y`` grows downwards. Details
and source in ``docs/classification-spec.md`` (section 1).
"""

from dataclasses import dataclass
from enum import IntEnum


class Indice(IntEnum):
    """MediaPipe indices used by the kinematic classification."""

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
    """Point in image pixels (``y`` grows downwards)."""

    x: float
    y: float


@dataclass(frozen=True, slots=True)
class Landmark:
    """Normalized landmark (0-1) with its probability of being visible."""

    x: float
    y: float
    visibilidad: float


@dataclass(frozen=True, slots=True)
class Pose:
    """Pose of one person in a frame, with the image size in pixels."""

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
        """Converts a normalized landmark to pixels.

        This is needed because MediaPipe normalizes ``x`` by the width and ``y`` by the height:
        without this conversion, distances and proportions come out distorted when the image is
        not square.
        """
        lm = self.landmarks[indice]
        return Punto(lm.x * self.ancho, lm.y * self.alto)

    def visibles(self, visibilidad_min: float) -> list[Punto]:
        """Landmarks in pixels whose visibility reaches the minimum."""
        return [
            Punto(lm.x * self.ancho, lm.y * self.alto)
            for lm in self.landmarks
            if lm.visibilidad >= visibilidad_min
        ]
