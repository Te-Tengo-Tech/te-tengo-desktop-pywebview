"""Advanced mode (US-32): what each camera detects and decides, in plain language, only on the PC.

* **Live log** (CA-32.2): ``Narrador`` turns what a camera's capture loop sees into short Spanish
  lines («Persona detectada en la Sala», «Posible caída: ventana de 1,48 s», «Imagen descartada:
  no se ven los tobillos»; the prototype's ``LOG`` in ``core.js``)
  and logs them with ``extra={"diario": …}``. ``ManejadorDiario``, a logging handler, keeps them
  in an in-memory ring buffer per camera (``Diario``) with their technical line («Ver línea
  técnica»): ``2026-09-23T10:41:51.482-05:00 INFO clasificador fase=INICIO_CAIDA v=0.034 …``.
  The window reads new lines twice per second. Lines are only kept while the advanced mode is
  on (CA-32.1); they are never written anywhere else than the program's own log file.
* **Meters** (CA-32.3, CA-32.4): ``Medidores`` keeps the latest analysis of a camera (frame
  rate, analysis time, person, key points' visibility, the three measures against their
  thresholds, the phase with its timers and the skeleton's points) for the «Medidores» view.
"""

import logging
import math
import threading
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, tzinfo
from typing import Any

from te_tengo_deteccion.clasificacion.estados import (
    ClasificadorCinematico,
    Evento,
    Fase,
    TipoEvento,
)
from te_tengo_deteccion.pose.schemas import Indice, Pose

logger = logging.getLogger("te_tengo_captura.diario")

CAPACIDAD = 2000  # lines kept per camera
DESCARTE_CADA_S = (
    10.0  # «Imagen descartada» at most every 10 s (it would repeat 8 times per second)
)
SIN_PERSONA_S = 2.0  # «Sin persona en la imagen» once nobody was seen for 2 s

# The skeleton of the meters (core.js ``skelG``): MediaPipe indexes of the drawn joints.
ARTICULACIONES = {
    "h": Indice.NARIZ,
    "sL": Indice.HOMBRO_IZQUIERDO,
    "sR": Indice.HOMBRO_DERECHO,
    "eL": 13,
    "eR": 14,
    "wL": 15,
    "wR": 16,
    "hL": Indice.CADERA_IZQUIERDA,
    "hR": Indice.CADERA_DERECHA,
    "kL": Indice.RODILLA_IZQUIERDA,
    "kR": Indice.RODILLA_DERECHA,
    "aL": Indice.TOBILLO_IZQUIERDO,
    "aR": Indice.TOBILLO_DERECHO,
}
VISIBILIDADES = {
    "Nariz": (Indice.NARIZ,),
    "Hombros": (Indice.HOMBRO_IZQUIERDO, Indice.HOMBRO_DERECHO),
    "Caderas": (Indice.CADERA_IZQUIERDA, Indice.CADERA_DERECHA),
    "Tobillos": (Indice.TOBILLO_IZQUIERDO, Indice.TOBILLO_DERECHO),
}


@dataclass(frozen=True, slots=True)
class Linea:
    id: int
    camara: str
    hora: str  # «10:41:52», the PC's time
    k: str  # filter: persona, evento, descarte, conexion, programa
    tono: str  # caida, inestable, calma, aviso, persona or ""
    icono: str
    texto: str
    tecnica: str

    def a_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "t": self.hora,
            "k": self.k,
            "tone": self.tono,
            "i": self.icono,
            "m": self.texto,
            "x": self.tecnica,
        }


class Diario:
    """Ring buffers of lines per camera, while the advanced mode is on."""

    def __init__(self, capacidad: int = CAPACIDAD) -> None:
        self._capacidad = capacidad
        self._lineas: dict[str, deque[Linea]] = {}
        self._candado = threading.Lock()
        self._siguiente = 1
        self.activo = False

    def agregar(
        self, camara: str, k: str, tono: str, icono: str, texto: str, tecnica: str, hora: str
    ) -> None:
        if not self.activo:
            return
        with self._candado:
            linea = Linea(self._siguiente, camara, hora, k, tono, icono, texto, tecnica)
            self._siguiente += 1
            self._lineas.setdefault(camara, deque(maxlen=self._capacidad)).append(linea)

    def desde(self, camara: str, ultimo: int = 0) -> list[Linea]:
        with self._candado:
            return [linea for linea in self._lineas.get(camara, ()) if linea.id > ultimo]

    def vaciar(self) -> None:
        with self._candado:
            self._lineas.clear()


class ManejadorDiario(logging.Handler):
    """Feeds ``Diario`` with the records that carry ``extra={"diario": {...}}``."""

    def __init__(self, diario: Diario, zona: tzinfo | None = None) -> None:
        super().__init__(logging.DEBUG)
        self._diario = diario
        self._zona = zona

    def emit(self, registro: logging.LogRecord) -> None:
        datos = getattr(registro, "diario", None)
        if not isinstance(datos, dict) or not self._diario.activo:
            return
        try:
            momento = datetime.fromtimestamp(registro.created, UTC).astimezone(self._zona)
            # The technical text carries its own level word, as in the prototype («INFO …»).
            tecnica = f"{momento.isoformat(timespec='milliseconds')} {datos.get('tecnica', '')}"
            self._diario.agregar(
                str(datos.get("camara", "")),
                str(datos.get("k", "programa")),
                str(datos.get("tono", "")),
                str(datos.get("icono", "monitor")),
                registro.getMessage(),
                tecnica,
                momento.strftime("%H:%M:%S"),
            )
        except Exception:  # a log line must never break the capture
            self.handleError(registro)


def anotar(
    camara: str,
    k: str,
    tono: str,
    icono: str,
    texto: str,
    tecnica: str,
    nivel: int = logging.INFO,
) -> None:
    """Logs one plain-language line of a camera (the file log gets it too)."""
    logger.log(
        nivel,
        "%s",
        texto,
        extra={
            "diario": {"camara": camara, "k": k, "tono": tono, "icono": icono, "tecnica": tecnica}
        },
    )


def _num(valor: float | None, decimales: int = 3) -> str:
    if valor is None or not math.isfinite(valor):
        return "-"
    return f"{valor:.{decimales}f}"


@dataclass
class Medicion:
    """The latest analysis of one camera (the «Medidores» view)."""

    persona: bool = False
    m1: float | None = None  # hip descent speed, bodies/s
    m2: float | None = None  # centre line angle with the floor, degrees
    m3: float | None = None  # width/height ratio
    cabeza_bajo_pies: bool = False
    fase: int = 0  # 0 De pie, 1 Posible caída, 2 En el suelo, 3 Caída confirmada
    ventana: float | None = None  # seconds left of the 1.48 s window
    suelo: float = 0.0  # seconds on the floor
    visibilidad: dict[str, float] = field(default_factory=dict)
    esqueleto: dict[str, tuple[float, float]] = field(default_factory=dict)
    umbral_v: float = 0.01
    umbral_angulo: float = 45.0
    umbral_razon: float = 1.0
    umbral_visibilidad: float = 0.5
    ventana_total: float = 1.48
    confirmacion: float = 30.0


class Narrador:
    """Watches one camera's analysis and tells it in plain language; keeps its meters."""

    def __init__(
        self,
        camara: Callable[[], str],
        habitacion: Callable[[], str],
        dispositivo: Callable[[], str],
        reloj: Callable[[], float],
    ) -> None:
        self._camara = camara
        self._habitacion = habitacion
        self._dispositivo = dispositivo
        self._reloj = reloj
        self.medicion = Medicion()
        self._persona = False
        self._sin_persona_desde: float | None = None
        self._fase = Fase.NORMAL
        self._m1 = False
        self._ultimo_descarte = -math.inf
        self._webcam: bool | None = None
        self._en_linea: bool | None = None
        self._pausada: datetime | None = None
        self._confirmada = False

    # ------------------------------------------------------------------ per frame (capture thread)

    def analizado(
        self,
        instante: float,
        pose: Pose | None,
        clasificador: ClasificadorCinematico,
        eventos: list[Evento],
    ) -> None:
        u = clasificador.umbrales
        m = self.medicion
        m.umbral_v = u.velocidad_descenso_min or 0.0
        m.umbral_angulo = u.angulo_linea_central_max_grados
        m.umbral_razon = u.razon_ancho_alto_min
        m.umbral_visibilidad = u.visibilidad_min
        m.ventana_total = u.ventana_reaccion_s
        m.confirmacion = u.confirmacion_suelo_s
        camara, sala = self._camara(), self._habitacion()
        ahora = self._reloj()
        if pose is None:
            m.persona = False
            if self._persona:
                if self._sin_persona_desde is None:
                    self._sin_persona_desde = ahora
                elif ahora - self._sin_persona_desde >= SIN_PERSONA_S:
                    self._persona = False
                    anotar(
                        camara,
                        "persona",
                        "",
                        "person",
                        "Sin persona en la imagen",
                        "INFO pose persona=0",
                    )
        else:
            self._sin_persona_desde = None
            m.persona = True
            m.visibilidad = {
                nombre: sum(pose.landmarks[i].visibilidad for i in indices) / len(indices)
                for nombre, indices in VISIBILIDADES.items()
            }
            m.esqueleto = {
                clave: (pose.landmarks[i].x, pose.landmarks[i].y)
                for clave, i in ARTICULACIONES.items()
            }
            if not self._persona:
                self._persona = True
                visible = sum(lm.visibilidad for lm in pose.landmarks) / len(pose.landmarks)
                anotar(
                    camara,
                    "persona",
                    "persona",
                    "person",
                    f"Persona detectada en {_en(sala)}",
                    f"INFO pose persona=1 puntos=33 visibilidad_media={visible:.2f}",
                )
            ultima = clasificador.ultima_medicion
            if ultima is not None and ultima.instante == instante:
                p = ultima.parametros
                m.m1, m.m2, m.m3 = ultima.velocidad, p.angulo_grados, p.razon_ancho_alto
                m.cabeza_bajo_pies = p.cabeza_bajo_pies
                if not p.puntos_visibles and ahora - self._ultimo_descarte >= DESCARTE_CADA_S:
                    self._ultimo_descarte = ahora
                    tobillos = m.visibilidad.get("Tobillos", 0.0)
                    anotar(
                        camara,
                        "descarte",
                        "aviso",
                        "eyeOff",
                        "Imagen descartada: no se ven los tobillos"
                        if tobillos < u.visibilidad_min
                        else "Imagen descartada: no se ven bien los puntos del cuerpo",
                        "DEBUG calidad descartada=1 motivo=puntos_no_visibles "
                        f"vis_tobillo={tobillos:.2f} min={u.visibilidad_min}",
                    )
                m1 = ultima.velocidad is not None and ultima.velocidad >= (
                    u.velocidad_descenso_min or math.inf
                )
                if m1 and not self._m1:
                    anotar(
                        camara,
                        "evento",
                        "inestable",
                        "arrowDown",
                        "La cadera bajó rápido (sobre el umbral)",
                        f"INFO clasificador M1=1 v_cadera={_num(ultima.velocidad)} "
                        f"umbral_v={u.velocidad_descenso_min}",
                    )
                self._m1 = m1
        self._fase_y_eventos(clasificador, instante, eventos)

    def _fase_y_eventos(
        self, clasificador: ClasificadorCinematico, instante: float, eventos: list[Evento]
    ) -> None:
        m, camara = self.medicion, self._camara()
        tiempos = clasificador.tiempos(instante)
        fase = clasificador.fase
        m.ventana = (
            max(0.0, m.ventana_total - tiempos.desde_inicio_caida)
            if tiempos.desde_inicio_caida is not None
            else None
        )
        m.suelo = tiempos.en_el_suelo or 0.0
        # The hip drop and the horizontal body can come in the same frame: the fall still
        # started (``INICIO_CAIDA``) before it ended on the floor.
        directa = self._fase is Fase.NORMAL and any(e.tipo is TipoEvento.CAIDA for e in eventos)
        if (fase is Fase.INICIO_CAIDA and self._fase is not Fase.INICIO_CAIDA) or directa:
            mm = clasificador.ultima_medicion
            v = mm.velocidad if mm else None
            theta = mm.parametros.angulo_grados if mm else None
            razon = mm.parametros.razon_ancho_alto if mm else None
            anotar(
                camara,
                "evento",
                "caida",
                "warn",
                f"Posible caída: ventana de {_coma(m.ventana_total)} s",
                f"INFO clasificador fase=INICIO_CAIDA v={_num(v)} theta={_num(theta, 1)} "
                f"P={_num(razon, 2)} M1=1 M2=1 M3=0",
            )
        if fase is not Fase.EN_EL_SUELO:
            self._confirmada = False
        for evento in eventos:
            self._evento(evento)
        self._fase = fase
        m.fase = (
            3
            if fase is Fase.EN_EL_SUELO and self._confirmada
            else 2
            if fase is Fase.EN_EL_SUELO
            else 1
            if fase is Fase.INICIO_CAIDA
            else 0
        )

    def _evento(self, evento: Evento) -> None:
        camara = self._camara()
        datos = " ".join(f"{k}={_num(v, 2)}" for k, v in evento.parametros.items())
        if evento.tipo is TipoEvento.CAIDA:
            anotar(
                camara,
                "evento",
                "caida",
                "warn",
                "Caída: en el suelo. Aviso enviado",
                (
                    "WARN clasificador fase=CAIDA en_suelo=1 evento=caida aviso=encolado " + datos
                ).rstrip(),
                logging.WARNING,
            )
        elif evento.tipo is TipoEvento.CAIDA_CONFIRMADA:
            self._confirmada = True
            anotar(
                camara,
                "evento",
                "caida",
                "warn",
                "Caída confirmada: 30 s en el suelo",
                f"WARN clasificador fase=CAIDA_CONFIRMADA t_suelo={_num(self.medicion.suelo, 1)}",
                logging.WARNING,
            )
        elif evento.tipo is TipoEvento.RECUPERACION:
            anotar(
                camara,
                "evento",
                "calma",
                "arrowUp",
                "Se levantó",
                f"INFO clasificador fase=DE_PIE evento=se_levanto {datos}".strip(),
            )
        elif evento.tipo is TipoEvento.MOVIMIENTO_INESTABLE:
            anotar(
                camara,
                "evento",
                "inestable",
                "warn",
                "Inestable: recuperó el equilibrio",
                f"WARN clasificador evento=inestable recuperado=1 {datos}".strip(),
                logging.WARNING,
            )
        elif evento.tipo is TipoEvento.DETECCION_NO_CONFIABLE:
            anotar(
                camara,
                "persona",
                "aviso",
                "eyeOff",
                "Sin persona en la imagen durante 5 minutos: revisa la luz y el encuadre",
                "WARN clasificador evento=deteccion_no_confiable",
                logging.WARNING,
            )

    # ------------------------------------------------------------------ every second (notifier)

    def estado(self, webcam: bool, en_linea: bool | None, pausada_hasta: datetime | None) -> None:
        camara, sala = self._camara(), self._habitacion()
        if webcam != self._webcam:
            if webcam:
                anotar(
                    camara,
                    "programa",
                    "",
                    "monitor",
                    f"Se abrió la cámara {_de(sala)} ({self._dispositivo()})",
                    f'INFO camara abierta nombre="{self._dispositivo()}"',
                )
            elif self._webcam is not None:
                anotar(
                    camara,
                    "conexion",
                    "aviso",
                    "videoOff",
                    "Cámara desconectada: revisa el cable USB",
                    "WARN camara desconectada",
                    logging.WARNING,
                )
            self._webcam = webcam
        if en_linea is not None and en_linea != self._en_linea:
            if en_linea is False:
                anotar(
                    camara,
                    "conexion",
                    "aviso",
                    "wifiOff",
                    "Sin internet: avisos en cola",
                    "WARN conexion estado=sin_red",
                    logging.WARNING,
                )
            elif self._en_linea is False:
                anotar(
                    camara,
                    "conexion",
                    "calma",
                    "wifi",
                    "Volvió internet: avisos enviados",
                    "INFO conexion estado=en_linea",
                )
            self._en_linea = en_linea
        if pausada_hasta != self._pausada:
            if pausada_hasta is not None:
                hora = pausada_hasta.astimezone().strftime("%H:%M")
                anotar(
                    camara,
                    "programa",
                    "",
                    "pause",
                    f"Cámara en pausa hasta las {hora}",
                    f"INFO captura pausada_hasta={pausada_hasta.isoformat()}",
                )
            self._pausada = pausada_hasta


_ARTICULO = {
    "sala": "la Sala",
    "dormitorio": "el Dormitorio",
    "cocina": "la Cocina",
    "comedor": "el Comedor",
    "pasillo": "el Pasillo",
}


def _en(sala: str) -> str:
    """«en la Sala», «en el Dormitorio» (core.js LOG)."""
    return _ARTICULO.get(sala.strip().lower(), f"«{sala}»")


def _de(sala: str) -> str:
    """«de la Sala», «del Dormitorio»."""
    texto = _en(sala)
    return "del " + texto[3:] if texto.startswith("el ") else "de " + texto


def _coma(valor: float) -> str:
    return f"{valor:.2f}".rstrip("0").rstrip(".").replace(".", ",")
