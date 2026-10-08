"""The picture the live view publishes for each mode (``docs/AGENT_CONTRACT.md``, "Live view").

* ``VIDEO``: the processed camera frame (480p, the one the pose was estimated on).
* ``VIDEO_CON_POSTURA``: that frame with the skeleton drawn on top.
* ``SOLO_POSTURA``: the skeleton on a plain brand-coloured background. The picture is built from
  a new array, never from the camera frame, so no image of the home leaves the PC.

The skeleton comes from the landmarks the capture loop already estimated for that frame; nothing
is estimated again. Colours are the brand's (``app.css`` of the prototype): ``--morado``
``#4A2A85``, ``--durazno`` ``#FFB59C`` and white. Lines are drawn without anti-aliasing, so a
``SOLO_POSTURA`` picture only has those three colours.
"""

import numpy as np

from te_tengo_captura.backend.modelos import ModoVista
from te_tengo_captura.captura.fuentes import Imagen
from te_tengo_deteccion.pose.schemas import Pose

# OpenCV images are BGR.
MORADO = (0x85, 0x2A, 0x4A)  # #4A2A85
DURAZNO = (0x9C, 0xB5, 0xFF)  # #FFB59C
BLANCO = (0xFF, 0xFF, 0xFF)

VISIBILIDAD_MIN = 0.5  # landmarks MediaPipe is not confident about are not drawn

# The body of MediaPipe's 33-landmark pose (face reduced to nose-eyes-ears; no fingers).
HUESOS: tuple[tuple[int, int], ...] = (
    (0, 2), (2, 7), (0, 5), (5, 8),  # nose, eyes, ears
    (11, 12), (11, 23), (12, 24), (23, 24),  # torso
    (11, 13), (13, 15), (12, 14), (14, 16),  # arms
    (23, 25), (25, 27), (24, 26), (26, 28),  # legs
    (27, 29), (29, 31), (27, 31), (28, 30), (30, 32), (28, 32),  # feet
)  # fmt: skip
ARTICULACIONES = tuple(sorted({i for hueso in HUESOS for i in hueso}))


def componer(imagen: Imagen, pose: Pose | None, modo: ModoVista) -> Imagen:
    """The picture to publish for ``modo``, with even dimensions (H.264 in ``yuv420p``)."""
    alto, ancho = (imagen.shape[0] // 2) * 2, (imagen.shape[1] // 2) * 2
    if modo is ModoVista.SOLO_POSTURA:
        lienzo = np.empty((alto, ancho, 3), dtype=np.uint8)
        lienzo[:] = MORADO
        if pose is not None:
            dibujar_esqueleto(lienzo, pose, hueso=BLANCO, borde=None)
        return lienzo
    lienzo = np.ascontiguousarray(imagen[:alto, :ancho])
    if modo is ModoVista.VIDEO_CON_POSTURA and pose is not None:
        lienzo = lienzo.copy()  # the capture loop keeps the original frame
        dibujar_esqueleto(lienzo, pose, hueso=BLANCO, borde=MORADO)
    return lienzo


def dibujar_esqueleto(
    lienzo: Imagen,
    pose: Pose,
    hueso: tuple[int, int, int],
    borde: tuple[int, int, int] | None,
) -> None:
    """Draws the bones and joints of ``pose`` on ``lienzo`` in place."""
    import cv2

    alto, ancho = lienzo.shape[:2]
    grosor = max(2, round(alto / 160))
    puntos: dict[int, tuple[int, int]] = {}
    for indice in ARTICULACIONES:
        landmark = pose.landmarks[indice]
        if landmark.visibilidad >= VISIBILIDAD_MIN:
            puntos[indice] = (round(landmark.x * ancho), round(landmark.y * alto))
    segmentos = [(puntos[a], puntos[b]) for a, b in HUESOS if a in puntos and b in puntos]
    if borde is not None:
        # A darker outline keeps a white skeleton visible on a bright room.
        for inicio, fin in segmentos:
            cv2.line(lienzo, inicio, fin, borde, grosor + 2, cv2.LINE_8)
    for inicio, fin in segmentos:
        cv2.line(lienzo, inicio, fin, hueso, grosor, cv2.LINE_8)
    for punto in puntos.values():
        if borde is not None:
            cv2.circle(lienzo, punto, grosor + 2, borde, -1, cv2.LINE_8)
        cv2.circle(lienzo, punto, grosor + 1, DURAZNO, -1, cv2.LINE_8)
