"""Local test window: video with the skeleton and an indicator panel on the right.

Text is drawn with Pillow and a system font (SF Pro on macOS, DejaVu on Linux, Segoe on
Windows), because OpenCV fonts have no accented characters and look pixelated.
"""

import contextlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from detection_worker.clasificacion.estados import Fase, Tiempos
from detection_worker.clasificacion.medicion import Medicion
from detection_worker.clasificacion.parametros import centro_cadera, extremos_linea_central
from detection_worker.clasificacion.umbrales import Umbrales
from detection_worker.pose.schemas import Indice, Pose

ALTO_VIDEO = 560
ANCHO_PANEL = 400
MARGEN = 22

# Palette (RGB). Te Tengo brand purple and status colors.
FONDO = (19, 16, 29)
TARJETA = (31, 26, 47)
LINEA = (52, 45, 74)
TEXTO = (238, 235, 246)
SUAVE = (152, 145, 172)
MORADO = (139, 108, 214)
VERDE = (61, 190, 139)
AMBAR = (242, 179, 61)
ROJO = (236, 84, 90)
CIAN = (72, 202, 228)

FUENTES = (
    "/System/Library/Fonts/SFNS.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
)

NOMBRE_EVENTO = {
    "caida": ("Caída detectada", ROJO),
    "caida_confirmada": ("Caída confirmada (30 s en el suelo)", ROJO),
    "movimiento_inestable": ("Movimiento inestable", AMBAR),
    "recuperacion": ("Se levantó", VERDE),
    "deteccion_no_confiable": ("Detección no confiable", AMBAR),
}

# MediaPipe Pose skeleton connections (pairs of landmark indices).
CONEXIONES = (
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16), (11, 23), (12, 24), (23, 24),
    (23, 25), (25, 27), (24, 26), (26, 28), (27, 29), (28, 30), (29, 31), (30, 32),
    (27, 31), (28, 32), (0, 11), (0, 12),
)  # fmt: skip
PUNTOS_FORMULAS = (
    Indice.NARIZ,
    Indice.CADERA_IZQUIERDA,
    Indice.CADERA_DERECHA,
    Indice.TOBILLO_IZQUIERDO,
    Indice.TOBILLO_DERECHO,
)


def _fuente(tamano: int, peso: str = "Regular") -> Any:
    for ruta in FUENTES:
        if Path(ruta).exists():
            try:
                fuente = ImageFont.truetype(ruta, tamano)
                with contextlib.suppress(OSError, ValueError):
                    fuente.set_variation_by_name(peso)  # SF Pro is a variable font
                return fuente
            except OSError:
                continue
    return ImageFont.load_default(size=tamano)


@dataclass
class Estado:
    """What is displayed for one frame."""

    pose: Pose | None
    medicion: Medicion | None
    fase: Fase | None  # None: measurement-only mode
    tiempos: Tiempos | None
    instante: float
    fps: float
    fuente_video: str
    eventos: list[tuple[float, str]] = field(default_factory=list)


class Visor:
    def __init__(self, umbrales: Umbrales) -> None:
        self._u = umbrales
        self._f = {
            "marca": _fuente(24, "Bold"),
            "titulo": _fuente(26, "Bold"),
            "normal": _fuente(15),
            "medio": _fuente(15, "Semibold"),
            "chico": _fuente(13),
            "seccion": _fuente(12, "Semibold"),
            "banner": _fuente(26, "Bold"),
        }

    # ------------------------------------------------------------------ composition

    def componer(self, imagen_bgr: Any, estado: Estado) -> Any:
        video = self._video(imagen_bgr, estado)
        alto, ancho = video.shape[:2]
        lienzo = Image.new("RGB", (ancho + ANCHO_PANEL, alto), FONDO)
        lienzo.paste(Image.fromarray(cv2.cvtColor(video, cv2.COLOR_BGR2RGB)), (0, 0))
        dibujo = ImageDraw.Draw(lienzo)
        self._banner(dibujo, estado, ancho)
        self._panel(dibujo, estado, ancho, alto)
        return cv2.cvtColor(np.asarray(lienzo), cv2.COLOR_RGB2BGR)

    def _color_fase(self, fase: Fase | None) -> tuple[int, int, int]:
        if fase is None:
            return MORADO
        return {Fase.NORMAL: VERDE, Fase.INICIO_CAIDA: AMBAR, Fase.EN_EL_SUELO: ROJO}[fase]

    def _video(self, imagen_bgr: Any, estado: Estado) -> Any:
        alto, ancho = imagen_bgr.shape[:2]
        escala = ALTO_VIDEO / alto
        video = cv2.resize(imagen_bgr, (round(ancho * escala), ALTO_VIDEO))
        pose = estado.pose
        if pose is None:
            return video
        r, g, b = self._color_fase(estado.fase)
        color = (b, g, r)

        def px(indice: int) -> tuple[int, int]:
            p = pose.en_pixeles(indice)
            return round(p.x * escala), round(p.y * escala)

        visibles = {
            i for i, lm in enumerate(pose.landmarks) if lm.visibilidad >= self._u.visibilidad_min
        }
        for a, b2 in CONEXIONES:
            if a in visibles and b2 in visibles:
                cv2.line(video, px(a), px(b2), color, 3, cv2.LINE_AA)
        for i in visibles:
            radio = 6 if i in PUNTOS_FORMULAS else 3
            cv2.circle(video, px(i), radio, (255, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(video, px(i), radio, color, 2, cv2.LINE_AA)
        if visibles:
            xs = [px(i)[0] for i in visibles]
            ys = [px(i)[1] for i in visibles]
            cv2.rectangle(
                video, (min(xs), min(ys)), (max(xs), max(ys)), (61, 179, 242), 1, cv2.LINE_AA
            )
        cabeza, pies = extremos_linea_central(pose)
        cv2.line(
            video,
            (round(cabeza.x * escala), round(cabeza.y * escala)),
            (round(pies.x * escala), round(pies.y * escala)),
            (228, 202, 72),
            2,
            cv2.LINE_AA,
        )
        cadera = centro_cadera(pose)
        cv2.drawMarker(
            video,
            (round(cadera.x * escala), round(cadera.y * escala)),
            (228, 202, 72),
            cv2.MARKER_CROSS,
            16,
            2,
            cv2.LINE_AA,
        )
        return video

    def _banner(self, d: Any, estado: Estado, ancho_video: int) -> None:
        recientes = [(t, e) for t, e in estado.eventos if estado.instante - t <= 3.0]
        if not recientes:
            return
        texto, color = NOMBRE_EVENTO.get(recientes[-1][1], (recientes[-1][1], MORADO))
        d.rounded_rectangle((16, 16, ancho_video - 16, 70), radius=14, fill=color)
        d.text(
            (ancho_video / 2, 43), texto.upper(), font=self._f["banner"], fill=FONDO, anchor="mm"
        )

    # ------------------------------------------------------------------ panel

    def _panel(self, d: Any, estado: Estado, x0: int, alto: int) -> None:
        x, ancho = x0 + MARGEN, ANCHO_PANEL - 2 * MARGEN
        d.line((x0, 0, x0, alto), fill=LINEA, width=1)

        # Header
        d.text((x, 20), "Te Tengo", font=self._f["marca"], fill=MORADO)
        d.text((x, 50), "Prueba del clasificador", font=self._f["chico"], fill=SUAVE)
        d.text(
            (x + ancho, 24), f"{estado.fps:.1f} fps", font=self._f["medio"], fill=TEXTO, anchor="ra"
        )
        d.text((x + ancho, 46), estado.fuente_video, font=self._f["chico"], fill=SUAVE, anchor="ra")

        y = self._tarjeta_fase(d, estado, x, 78, ancho)
        y = self._persona(d, estado, x, y + 12, ancho)
        y = self._condiciones(d, estado, x, y + 16, ancho)
        self._eventos(d, estado, x, y + 14, ancho, alto)
        d.text(
            (x, alto - 26),
            "q salir   ·   r reiniciar   ·   c guardar captura",
            font=self._f["chico"],
            fill=SUAVE,
        )

    def _barra(
        self, d: Any, x: int, y: int, ancho: int, fraccion: float, color: tuple[int, int, int]
    ) -> None:
        d.rounded_rectangle((x, y, x + ancho, y + 6), radius=3, fill=LINEA)
        fraccion = max(0.0, min(1.0, fraccion))
        if fraccion > 0:
            d.rounded_rectangle(
                (x, y, x + max(6, round(ancho * fraccion)), y + 6), radius=3, fill=color
            )

    def _tarjeta_fase(self, d: Any, e: Estado, x: int, y: int, ancho: int) -> int:
        alto = 92
        d.rounded_rectangle((x, y, x + ancho, y + alto), radius=14, fill=TARJETA)
        color = self._color_fase(e.fase)
        d.rounded_rectangle((x, y, x + 5, y + alto), radius=3, fill=color)
        d.text((x + 18, y + 12), "ESTADO", font=self._f["seccion"], fill=SUAVE)
        t, u = e.tiempos, self._u
        if e.fase is None:
            titulo, detalle, avance = "Solo medición", "Sin umbral de velocidad: no clasifica", None
        elif e.fase is Fase.NORMAL:
            titulo, detalle, avance = "Normal", "Vigilando: sin caída en curso", None
        elif e.fase is Fase.INICIO_CAIDA:
            transcurrido = t.desde_inicio_caida if t and t.desde_inicio_caida else 0.0
            titulo = "Posible caída"
            detalle = (
                f"Esperando postura horizontal · {transcurrido:.1f} / {u.ventana_reaccion_s:.1f} s"
            )
            avance = transcurrido / u.ventana_reaccion_s
        else:
            en_suelo = t.en_el_suelo if t and t.en_el_suelo else 0.0
            titulo = "En el suelo"
            if en_suelo >= u.confirmacion_suelo_s:
                detalle, avance = f"Caída confirmada · {en_suelo:.0f} s en el suelo", 1.0
            else:
                detalle = f"Confirma a los {u.confirmacion_suelo_s:.0f} s · lleva {en_suelo:.0f} s"
                avance = en_suelo / u.confirmacion_suelo_s
        d.text((x + 18, y + 30), titulo, font=self._f["titulo"], fill=color)
        d.text((x + 18, y + 64), detalle, font=self._f["chico"], fill=SUAVE)
        if avance is not None:
            self._barra(d, x + 18, y + 82, ancho - 36, avance, color)
        return y + alto

    def _persona(self, d: Any, e: Estado, x: int, y: int, ancho: int) -> int:
        if e.pose is None:
            chips = [("Sin persona visible", ROJO)]
        else:
            visibles = e.medicion is not None and e.medicion.parametros.puntos_visibles
            chips = [
                ("Persona detectada", VERDE),
                ("Puntos clave visibles" if visibles else "Puntos clave poco visibles",
                 VERDE if visibles else AMBAR),
            ]  # fmt: skip
        cx = x
        for texto, color in chips:
            ancho_txt = d.textlength(texto, font=self._f["chico"])
            d.rounded_rectangle((cx, y, cx + ancho_txt + 30, y + 26), radius=13, fill=TARJETA)
            d.ellipse((cx + 10, y + 9, cx + 18, y + 17), fill=color)
            d.text((cx + 24, y + 13), texto, font=self._f["chico"], fill=TEXTO, anchor="lm")
            cx += ancho_txt + 38
        return y + 26

    def _condicion(
        self,
        d: Any,
        x: int,
        y: int,
        ancho: int,
        codigo: str,
        nombre: str,
        valor: str,
        fraccion: float,
        marca: float,
        cumple: bool | None,
    ) -> int:
        # Amber = the condition is met; red is reserved for the fall.
        color = SUAVE if cumple is None else (AMBAR if cumple else VERDE)
        d.text((x, y), codigo, font=self._f["medio"], fill=color)
        d.text((x + 34, y), nombre, font=self._f["normal"], fill=TEXTO)
        d.text((x + ancho, y), valor, font=self._f["medio"], fill=TEXTO, anchor="ra")
        self._barra(d, x, y + 26, ancho, fraccion, color)
        tick = x + round(ancho * max(0.0, min(1.0, marca)))
        d.line((tick, y + 22, tick, y + 36), fill=TEXTO, width=2)
        return y + 46

    def _condiciones(self, d: Any, e: Estado, x: int, y: int, ancho: int) -> int:
        d.text((x, y), "CONDICIONES DE CAÍDA", font=self._f["seccion"], fill=SUAVE)
        d.text(
            (x + ancho, y),
            "ámbar = se cumple  ·  | = umbral",
            font=self._f["chico"],
            fill=SUAVE,
            anchor="ra",
        )
        y += 22
        u, m = self._u, e.medicion
        if m is None:
            d.text(
                (x, y),
                "Sin pose: no hay mediciones en este fotograma.",
                font=self._f["normal"],
                fill=SUAVE,
            )
            return y + 24
        p, v = m.parametros, m.velocidad
        v_min = u.velocidad_descenso_min
        m1 = None if v is None or v_min is None else v >= v_min
        y = self._condicion(
            d, x, y, ancho, "M1", "Bajada de la cadera",
            "—" if v is None else f"{v:.2f} cuerpos/s",
            0 if v is None else v / 2, (v_min or 0) / 2, m1,
        )  # fmt: skip
        m2 = p.angulo_grados < u.angulo_linea_central_max_grados or p.cabeza_bajo_pies
        y = self._condicion(
            d, x, y, ancho, "M2", "Inclinación del cuerpo",
            f"{p.angulo_grados:.0f}°", p.angulo_grados / 90,
            u.angulo_linea_central_max_grados / 90, m2,
        )  # fmt: skip
        m3 = p.razon_ancho_alto >= u.razon_ancho_alto_min or p.cabeza_bajo_pies
        razon = p.razon_ancho_alto
        y = self._condicion(
            d, x, y, ancho, "M3", "Ancho / alto del cuerpo",
            "∞" if razon == float("inf") else f"{razon:.2f}",
            min(razon, 2.5) / 2.5, u.razon_ancho_alto_min / 2.5, m3,
        )  # fmt: skip
        cabeza = "Sí (cuenta como M2 y M3)" if p.cabeza_bajo_pies else "No"
        d.text((x, y), f"Cabeza bajo los pies: {cabeza}", font=self._f["chico"], fill=SUAVE)
        y += 20
        if e.fase is Fase.EN_EL_SUELO and e.tiempos is not None:
            erguido = e.tiempos.erguido or 0.0
            d.text(
                (x, y),
                f"Erguido para «se levantó»: {erguido:.1f} / {u.persistencia_erguido_s:.1f} s",
                font=self._f["chico"],
                fill=SUAVE,
            )
            self._barra(d, x, y + 18, ancho, erguido / u.persistencia_erguido_s, VERDE)
            y += 28
        return y

    def _eventos(self, d: Any, e: Estado, x: int, y: int, ancho: int, alto: int) -> None:
        d.text((x, y), "EVENTOS", font=self._f["seccion"], fill=SUAVE)
        y += 22
        if not e.eventos:
            d.text((x, y), "Todavía no hay eventos.", font=self._f["normal"], fill=SUAVE)
            return
        espacio = max(1, (alto - 40 - y) // 26)
        for instante, tipo in reversed(e.eventos[-espacio:]):
            texto, color = NOMBRE_EVENTO.get(tipo, (tipo, MORADO))
            minutos, segundos = divmod(int(instante), 60)
            d.ellipse((x, y + 5, x + 9, y + 14), fill=color)
            d.text((x + 18, y), texto, font=self._f["normal"], fill=TEXTO)
            d.text(
                (x + ancho, y),
                f"{minutos:02d}:{segundos:02d}",
                font=self._f["chico"],
                fill=SUAVE,
                anchor="ra",
            )
            y += 26
