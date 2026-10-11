"""The QR of «Vincular esta PC»: ``verification_uri_complete`` as an SVG path (D-28.1).

The window draws it like the prototype's ``qrSVG`` (dark modules in ``--ink`` on white, two
modules of quiet zone) with the app icon over its centre. Error correction level H (30 %) keeps
it readable with the icon covering the middle. ``segno`` is pure Python and needs no image
library.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CodigoQr:
    modulos: int  # side, in modules
    ruta: str  # SVG path of the dark modules, one unit per module


def codigo_qr(texto: str) -> CodigoQr:
    import segno

    qr = segno.make(texto, error="h", micro=False, boost_error=False)
    filas = [bytes(fila) for fila in qr.matrix]
    partes = []
    for y, fila in enumerate(filas):
        x = 0
        while x < len(fila):
            if fila[x]:
                inicio = x
                while x < len(fila) and fila[x]:
                    x += 1
                partes.append(f"M{inicio} {y}h{x - inicio}v1h-{x - inicio}z")
            else:
                x += 1
    return CodigoQr(len(filas), "".join(partes))
