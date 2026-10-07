"""Synthetic poses for the tests (640 × 480 px image, coordinates in pixels)."""

from detection_worker.pose.schemas import TOTAL_LANDMARKS, Indice, Landmark, Pose

ANCHO, ALTO = 640, 480
Px = tuple[float, float]


def pose(cabeza: Px, cadera: Px, tobillos: Px, extra: Px | None = None) -> Pose:
    """Builds a pose with the nose, the hips and the ankles at the given points.

    The remaining landmarks are placed at the hip so they do not alter the body rectangle.
    ``extra`` (a wrist) makes it possible to enlarge the rectangle on purpose.
    """
    puntos: list[Px] = [cadera] * TOTAL_LANDMARKS
    puntos[Indice.NARIZ] = cabeza
    puntos[Indice.CADERA_IZQUIERDA] = puntos[Indice.CADERA_DERECHA] = cadera
    puntos[Indice.TOBILLO_IZQUIERDO] = puntos[Indice.TOBILLO_DERECHO] = tobillos
    if extra is not None:
        puntos[15] = extra  # left wrist
    return Pose(tuple(Landmark(x / ANCHO, y / ALTO, 1.0) for x, y in puntos), ANCHO, ALTO)


# Standing person: vertical center line (θ = 90°), tall and narrow rectangle (P < 1).
DE_PIE = pose(cabeza=(320, 100), cadera=(320, 220), tobillos=(320, 340))

# Person lying on the floor: θ = 0°, P ≥ 1.
TENDIDA = pose(cabeza=(200, 400), cadera=(320, 400), tobillos=(440, 400))

# Tilted during a fall: hip lower, θ ≈ 37° (< 45°) and P ≈ 1.33 (≥ 1).
CAYENDO = pose(cabeza=(420, 250), cadera=(330, 300), tobillos=(300, 340))

# Loss of balance: same tilt, but a raised arm keeps P < 1.
TAMBALEO = pose(cabeza=(420, 250), cadera=(330, 300), tobillos=(300, 340), extra=(330, 150))

# Crouching: the hip drops quickly but the body stays vertical (θ = 90°).
AGACHADA = pose(cabeza=(320, 200), cadera=(320, 300), tobillos=(320, 340))

# Leaning: θ ≈ 40° with the hip at the same height as when standing (no descent).
INCLINADA = pose(cabeza=(450, 230), cadera=(320, 220), tobillos=(320, 340), extra=(320, 100))
