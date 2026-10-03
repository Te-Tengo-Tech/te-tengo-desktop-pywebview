"""Poses sintéticas para las pruebas (imagen de 640 × 480 px, coordenadas en píxeles)."""

from detection_worker.pose.schemas import TOTAL_LANDMARKS, Indice, Landmark, Pose

ANCHO, ALTO = 640, 480
Px = tuple[float, float]


def pose(cabeza: Px, cadera: Px, tobillos: Px, extra: Px | None = None) -> Pose:
    """Arma una pose con la nariz, las caderas y los tobillos en los puntos indicados.

    El resto de landmarks se coloca en la cadera para no alterar el rectángulo del cuerpo.
    ``extra`` (una muñeca) permite agrandar el rectángulo a propósito.
    """
    puntos: list[Px] = [cadera] * TOTAL_LANDMARKS
    puntos[Indice.NARIZ] = cabeza
    puntos[Indice.CADERA_IZQUIERDA] = puntos[Indice.CADERA_DERECHA] = cadera
    puntos[Indice.TOBILLO_IZQUIERDO] = puntos[Indice.TOBILLO_DERECHO] = tobillos
    if extra is not None:
        puntos[15] = extra  # muñeca izquierda
    return Pose(tuple(Landmark(x / ANCHO, y / ALTO, 1.0) for x, y in puntos), ANCHO, ALTO)


# Persona de pie: línea central vertical (θ = 90°), rectángulo alto y angosto (P < 1).
DE_PIE = pose(cabeza=(320, 100), cadera=(320, 220), tobillos=(320, 340))

# Persona tendida en el suelo: θ = 0°, P ≥ 1.
TENDIDA = pose(cabeza=(200, 400), cadera=(320, 400), tobillos=(440, 400))

# Inclinada durante una caída: cadera más abajo, θ ≈ 37° (< 45°) y P ≈ 1,33 (≥ 1).
CAYENDO = pose(cabeza=(420, 250), cadera=(330, 300), tobillos=(300, 340))

# Pérdida de equilibrio: misma inclinación, pero un brazo arriba mantiene P < 1.
TAMBALEO = pose(cabeza=(420, 250), cadera=(330, 300), tobillos=(300, 340), extra=(330, 150))

# Agacharse: la cadera baja rápido pero el cuerpo sigue vertical (θ = 90°).
AGACHADA = pose(cabeza=(320, 200), cadera=(320, 300), tobillos=(320, 340))

# Inclinarse: θ ≈ 40° con la cadera a la misma altura que de pie (sin descenso).
INCLINADA = pose(cabeza=(450, 230), cadera=(320, 220), tobillos=(320, 340), extra=(320, 100))
