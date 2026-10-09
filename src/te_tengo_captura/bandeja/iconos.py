"""Tray icon images, drawn from the brand app icon (``icono-app.svg``, «La T que sostiene»).

The geometry is the SVG's (120 × 120 viewBox): a ``#4A2A85`` rounded square (rx 28), a white
stroke of 13 with round caps (the stem ``M60 60 V96`` and the arms ``M22 38 Q60 80 98 38``) and
a ``#FFB59C`` dot at (60, 38) with radius 11. The status dot of ``trayState`` goes in the
bottom-right corner with the colours of ``.tdot`` in the prototype's CSS.
"""

from PIL import Image, ImageDraw

MORADO = "#4A2A85"
DURAZNO = "#FFB59C"
# .tdot: green while sending, grey while paused, amber on a problem; ring in the taskbar colour.
PUNTOS = {"ok": "#1C7A4C", "idle": "#8C849E", "warn": "#D98A00"}
ANILLO = "#F3F3F6"
_SOBREMUESTREO = 4


def _bezier(
    p0: tuple[float, float], p1: tuple[float, float], p2: tuple[float, float], n: int = 48
) -> list[tuple[float, float]]:
    puntos = []
    for i in range(n + 1):
        t = i / n
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t**2 * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t**2 * p2[1]
        puntos.append((x, y))
    return puntos


def icono(punto: str | None = None, tamano: int = 64) -> Image.Image:
    """The app icon at ``tamano`` px, with the status dot ``ok``, ``idle`` or ``warn``."""
    lado = tamano * _SOBREMUESTREO
    e = lado / 120  # SVG units → pixels
    imagen = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(imagen)
    dibujo.rounded_rectangle((0, 0, lado - 1, lado - 1), radius=28 * e, fill=MORADO)

    grosor = 13 * e
    trazos: list[list[tuple[float, float]]] = [
        [(60, 60), (60, 96)],
        _bezier((22, 38), (60, 80), (98, 38)),
    ]
    for trazo in trazos:
        escalado = [(x * e, y * e) for x, y in trazo]
        dibujo.line(escalado, fill="white", width=round(grosor), joint="curve")
        for x, y in (escalado[0], escalado[-1]):  # stroke-linecap: round
            dibujo.ellipse(
                (x - grosor / 2, y - grosor / 2, x + grosor / 2, y + grosor / 2), fill="white"
            )
    dibujo.ellipse(((60 - 11) * e, (38 - 11) * e, (60 + 11) * e, (38 + 11) * e), fill=DURAZNO)

    if punto is not None:
        radio = lado * 0.17
        cx = cy = lado - radio - lado * 0.02
        anillo = radio + lado * 0.05
        dibujo.ellipse((cx - anillo, cy - anillo, cx + anillo, cy + anillo), fill=ANILLO)
        dibujo.ellipse((cx - radio, cy - radio, cx + radio, cy + radio), fill=PUNTOS[punto])
    return imagen.resize((tamano, tamano), Image.Resampling.LANCZOS)
