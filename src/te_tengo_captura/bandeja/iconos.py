"""Tray and app icon images, drawn from the Te Tengo brand app icon (``icono-app.svg``).

The brand kit's symbol is two figures hugging: the violet one hugs, the coral one is hugged
(``MARK_VH``, ``MARK_ARM``, ``MARK_CH`` and ``MARK_BODY`` of the prototype's ``core.js``). The app
icon is a ``#4B2E83`` rounded square (122 × 122 viewBox, rx 28) with the symbol scaled by 0.705
and moved by (18, 18): the hugging figure in white, the hugged one in coral ``#FF8F7E``. The paths
only use absolute ``M``, ``C`` and ``Z`` commands, flattened here into polygons for Pillow. The
status dot of ``trayState`` goes in the bottom-right corner with the colours of ``.tdot``.
"""

import re

from PIL import Image, ImageDraw

MORADO = "#4B2E83"
CORAL = "#FF8F7E"
# .tdot: green while caring, grey while paused, amber on a problem, violet while someone watches
# live; «off» (not linked) is an empty grey ring. The ring around it has the taskbar's colour.
PUNTOS = {"ok": "#1C7A4C", "idle": "#8E879C", "warn": "#D98A00", "live": MORADO, "off": "#FFFFFF"}
ANILLO = "#F6F3F6"
ANILLO_APAGADO = "#8E879C"
_SOBREMUESTREO = 4
_LADO_SVG = 122
_ESCALA_SIMBOLO, _DESPLAZAMIENTO = 0.705, 18.0

CABEZA_ABRAZA = (47.7, 24.4, 17.6)  # MARK_VH: cx, cy, r
CABEZA_ABRAZADA = (80.9, 39.8, 15.4)  # MARK_CH
BRAZO = (
    "M20.4 35.9 C21.9 35.6 23.0 35.8 24.4 36.2 C25.8 36.6 25.5 35.8 28.6 38.2 C31.6 40.7 "
    "38.3 47.6 42.5 51.0 C46.7 54.3 50.3 56.5 53.8 58.2 C57.3 59.9 59.6 60.6 63.3 61.1 "
    "C67.0 61.6 73.8 61.1 75.9 61.1 C75.3 61.9 74.1 64.4 72.4 65.9 C70.7 67.4 68.1 69.0 "
    "65.5 70.2 C62.9 71.4 59.5 72.4 56.7 72.9 C54.0 73.4 51.4 73.5 49.0 73.3 C46.7 73.2 "
    "44.6 72.8 42.6 72.1 C40.5 71.4 38.5 70.5 36.7 69.2 C35.0 67.9 33.4 66.3 32.0 64.3 "
    "C30.6 62.3 29.1 58.4 28.2 57.0 C27.4 55.7 27.4 56.3 26.9 56.3 C26.5 56.2 26.2 56.1 "
    "25.7 56.6 C25.2 57.2 24.5 58.2 24.2 59.5 C23.8 60.9 23.4 62.0 23.7 64.5 C24.0 67.1 "
    "24.6 71.8 25.9 75.0 C27.2 78.2 29.3 81.2 31.6 83.8 C34.0 86.5 37.5 89.2 40.0 91.0 "
    "C42.5 92.8 44.1 93.5 46.5 94.5 C48.8 95.6 51.6 96.6 54.0 97.2 C56.5 97.9 58.3 98.4 "
    "61.0 98.7 C63.7 99.0 68.7 98.8 70.5 99.1 C72.3 99.3 71.7 99.9 72.0 100.0 C71.7 100.9 "
    "71.3 103.2 70.1 105.0 C68.9 106.9 66.5 109.5 64.8 111.2 C63.0 112.8 60.9 114.1 59.3 "
    "114.9 C57.7 115.6 57.2 115.8 55.1 115.5 C53.1 115.1 49.9 114.3 46.9 112.9 C43.8 "
    "111.6 39.7 109.4 36.7 107.5 C33.7 105.5 31.3 103.8 28.7 101.4 C26.1 99.0 23.2 95.9 "
    "20.9 93.1 C18.5 90.3 16.5 87.0 14.9 84.4 C13.3 81.8 12.5 80.1 11.4 77.5 C10.4 74.8 "
    "9.3 71.8 8.7 68.7 C8.0 65.6 7.5 61.9 7.5 58.9 C7.4 56.0 7.7 53.6 8.3 51.0 C8.9 48.4 "
    "9.8 45.2 11.0 43.1 C12.2 40.9 13.7 39.1 15.2 37.9 C16.8 36.7 18.8 36.1 20.4 35.9Z"
)
CUERPO = (
    "M96.0 52.7 C97.5 52.7 99.5 52.9 101.0 53.4 C102.5 53.8 103.6 54.4 104.9 55.4 C106.1 "
    "56.4 107.5 57.9 108.4 59.3 C109.3 60.7 109.9 62.2 110.3 63.7 C110.8 65.2 111.1 66.5 "
    "111.2 68.3 C111.3 70.2 111.2 72.9 110.9 74.8 C110.6 76.7 110.4 77.7 109.6 79.8 "
    "C108.8 81.9 107.7 84.8 106.1 87.6 C104.4 90.4 101.9 93.8 99.5 96.5 C97.1 99.2 94.6 "
    "101.5 91.9 103.7 C89.1 105.8 86.6 107.7 83.1 109.5 C79.6 111.4 73.1 113.9 70.9 114.7 "
    "C68.7 115.6 70.1 114.7 69.9 114.7 C69.9 114.6 69.1 115.0 70.0 114.0 C71.0 112.9 74.1 "
    "110.1 75.5 108.4 C77.0 106.7 77.9 105.4 78.8 103.7 C79.6 102.0 80.4 99.5 80.6 98.2 "
    "C80.9 96.9 80.5 96.4 80.1 95.7 C79.7 94.9 79.7 94.2 78.3 93.9 C76.9 93.6 75.2 93.8 "
    "71.9 93.7 C68.5 93.6 62.3 93.8 58.2 93.1 C54.1 92.4 50.5 91.1 47.2 89.4 C43.9 87.7 "
    "40.5 84.9 38.2 82.9 C36.0 81.0 34.8 79.0 33.9 77.6 C33.0 76.1 33.0 74.8 32.9 74.3 "
    "C33.1 74.2 32.8 73.6 34.2 74.1 C35.5 74.6 38.6 76.5 41.0 77.2 C43.4 78.0 46.1 78.5 "
    "48.7 78.7 C51.3 78.9 54.0 78.9 56.7 78.6 C59.5 78.2 62.6 77.4 65.0 76.6 C67.5 75.9 "
    "69.3 75.0 71.4 73.8 C73.4 72.7 74.5 72.7 77.2 69.7 C80.0 66.7 85.6 58.5 88.1 55.8 "
    "C90.6 53.1 90.8 54.0 92.1 53.5 C93.4 53.0 94.5 52.7 96.0 52.7Z"
)


Punto = tuple[float, float]


def poligono(ruta: str, pasos: int = 16) -> list[Punto]:
    """The points of an SVG path made of ``M x y``, ``C x1 y1 x2 y2 x y`` and ``Z``."""
    numeros = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", ruta)]
    comandos = re.findall(r"[MCZ]", ruta)
    puntos: list[Punto] = []
    i = 0
    actual: Punto = (0.0, 0.0)
    for comando in comandos:
        if comando == "M":
            actual = (numeros[i], numeros[i + 1])
            i += 2
            puntos.append(actual)
        elif comando == "C":
            c1, c2, fin = (
                (numeros[i], numeros[i + 1]),
                (numeros[i + 2], numeros[i + 3]),
                (numeros[i + 4], numeros[i + 5]),
            )
            i += 6
            for paso in range(1, pasos + 1):
                t = paso / pasos
                u = 1 - t
                puntos.append(
                    (
                        u**3 * actual[0]
                        + 3 * u**2 * t * c1[0]
                        + 3 * u * t**2 * c2[0]
                        + t**3 * fin[0],
                        u**3 * actual[1]
                        + 3 * u**2 * t * c1[1]
                        + 3 * u * t**2 * c2[1]
                        + t**3 * fin[1],
                    )
                )
            actual = fin
    return puntos


def icono(punto: str | None = None, tamano: int = 64) -> Image.Image:
    """The app icon at ``tamano`` px, with the status dot ``ok``, ``idle``, ``warn``, ``live`` or
    ``off``."""
    lado = tamano * _SOBREMUESTREO
    e = lado / _LADO_SVG  # SVG units → pixels

    def simbolo(x: float, y: float) -> Punto:
        return (
            (_DESPLAZAMIENTO + x * _ESCALA_SIMBOLO) * e,
            (_DESPLAZAMIENTO + y * _ESCALA_SIMBOLO) * e,
        )

    imagen = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(imagen)
    dibujo.rounded_rectangle((0, 0, lado - 1, lado - 1), radius=28 * e, fill=MORADO)
    for (cx, cy, r), ruta, color in (
        (CABEZA_ABRAZA, BRAZO, "white"),
        (CABEZA_ABRAZADA, CUERPO, CORAL),
    ):
        x, y = simbolo(cx, cy)
        radio = r * _ESCALA_SIMBOLO * e
        dibujo.ellipse((x - radio, y - radio, x + radio, y + radio), fill=color)
        dibujo.polygon([simbolo(px, py) for px, py in poligono(ruta)], fill=color)

    if punto is not None:
        radio = lado * 0.17
        cx = cy = lado - radio - lado * 0.02
        anillo = radio + lado * 0.05
        dibujo.ellipse((cx - anillo, cy - anillo, cx + anillo, cy + anillo), fill=ANILLO)
        if punto == "off":
            dibujo.ellipse((cx - radio, cy - radio, cx + radio, cy + radio), fill=ANILLO_APAGADO)
            interior = radio * 0.62
            dibujo.ellipse(
                (cx - interior, cy - interior, cx + interior, cy + interior), fill=PUNTOS["off"]
            )
        else:
            dibujo.ellipse((cx - radio, cy - radio, cx + radio, cy + radio), fill=PUNTOS[punto])
    return imagen.resize((tamano, tamano), Image.Resampling.LANCZOS)
