"""The agent state the window and the tray show: one immutable value, one source of truth.

``derivar`` turns the raw inputs (the cameras of this PC, internet, consent, pauses, live view)
into an ``EstadoAgente`` with the priorities of ``health``, ``camStatus`` and ``trayState`` in the
desktop prototype (docs repo ``05-prototipos/app-escritorio/.impeccable/src/core.js``, copied to
``docs/references/desktop-prototype/src/core.js``):

* the summary (``health``): no webcam found › cameras not chosen yet › a camera does not answer ›
  no internet › no consent › a camera paused › someone watching live › all good;
* each camera's row (``camStatus``): disconnected › no consent › paused › live › no internet ›
  online;
* the tray dot (``trayState``): not linked › cameras not chosen › a camera lost › offline › no
  consent › live › paused › all good.

All the Spanish copy that depends on the state lives here, copied verbatim from ``core.js``
(UI term «habitación»); where the prototype has no sentence for a case the agent can reach
(several cameras lost or paused, nobody named as the viewer) the closest prototype sentence is
adapted and listed in ``docs/BLOCKERS.md``. The web UI only renders it. Fields named ``*_html``
are already escaped and may contain the prototype's ``<span class="mono">``; every other text is
plain and the UI escapes it.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, tzinfo
from enum import StrEnum
from html import escape
from typing import Any, Protocol

QUIEN_MIRA = "Un familiar"  # core.js osToast fallback: the contract does not say who watches
QUIEN_PAUSA = "la familia"  # core.js health fallback (``S.pauseBy||'la familia'``)


class Situacion(StrEnum):
    """The summary of the window (the ``health`` block), in priority order."""

    SIN_CAMARAS = "sin_camaras"  # a linked PC finds no webcam
    FALTA_ELEGIR = "falta_elegir"  # a linked PC whose webcams have no room yet
    WEBCAM_DESCONECTADA = "webcam_desconectada"
    SIN_INTERNET = "sin_internet"
    SIN_CONSENTIMIENTO = "sin_consentimiento"
    EN_PAUSA = "en_pausa"
    EN_VIVO = "en_vivo"
    CUIDANDO = "cuidando"


@dataclass(frozen=True, slots=True)
class CamaraEntradas:
    """One camera in use on this PC."""

    clave: str  # camaraId, or the device id while it has none
    nombre_habitacion: str
    dispositivo: str  # the webcam's name, e.g. «Webcam USB HD»
    webcam_conectada: bool
    pausada_hasta: datetime | None = None
    en_vivo_desde: datetime | None = None  # someone watches the live view (US-23)
    elegida_desde: str | None = None  # "app", "pc" or None (an installation)


@dataclass(frozen=True, slots=True)
class Webcam:
    """A webcam the PC detects (the «Cámaras» tab), in use or not."""

    clave: str
    nombre: str
    dispositivo_id: str | None
    nombre_habitacion: str | None  # None: «Sin usar»
    conectada: bool = True
    ocupada: bool = False  # another program holds it
    nueva: bool = False
    elegida_desde: str | None = None
    vista_previa: bool = True  # the local preview can be shown


@dataclass(frozen=True, slots=True)
class DatosPc:
    """What the folded «Datos de la instalación» and the tab bar say about this PC."""

    nombre: str
    sistema: str
    programa: str  # «Te Tengo Captura 0.5.0»
    vinculada_por: str | None = None  # the approver's name (linked PCs)
    vinculada_el: str | None = None  # «23/09/2026»
    instalada_el: str | None = None  # installations: «22/09/2026»


@dataclass(frozen=True, slots=True)
class Entradas:
    camaras: tuple[CamaraEntradas, ...]
    en_linea: bool | None  # None before the first answer: not shown as offline
    consentimiento: bool
    segundos_para_reintento: int
    webcams: tuple[Webcam, ...] = ()
    vinculada: bool = False  # a linked PC (PC link), not an installation
    webcams_detectadas: int | None = None  # linked PCs: how many webcams it found


@dataclass(frozen=True, slots=True)
class Accion:
    act: str  # data-act of the button: "rescan", "retryNow" or "toCams"
    texto: str
    icono: str


@dataclass(frozen=True, slots=True)
class Aviso:
    """``health``: the summary block at the top of «Estado»."""

    clase: str
    k: str
    icono: str
    titulo_html: str
    detalle_html: str
    accion: Accion | None


@dataclass(frozen=True, slots=True)
class EstadoCamara:
    """``camStatus``: the status of one camera's row."""

    k: str
    titulo: str
    detalle_html: str
    icono: str


@dataclass(frozen=True, slots=True)
class FilaCamara:
    clave: str
    habitacion: str
    dispositivo: str
    estado: EstadoCamara


@dataclass(frozen=True, slots=True)
class EstadoBandeja:
    """``trayState``: the dot of the tray icon (ok, idle, warn, live, off) and its tooltip."""

    k: str
    etiqueta: str


@dataclass(frozen=True, slots=True)
class Notificacion:
    """``osToast``: a system notification."""

    titulo: str
    texto: str


class Mostrable(Protocol):
    """What the window and the tray icon need: the page's JSON and the tray dot."""

    @property
    def bandeja(self) -> "EstadoBandeja": ...

    def a_json(self) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class Hogar:
    nombre_adulto_mayor: str
    direccion: str

    @property
    def primer_nombre(self) -> str:
        return self.nombre_adulto_mayor.split(" ")[0]


@dataclass(frozen=True, slots=True)
class EstadoAgente:
    situacion: Situacion
    entradas: Entradas
    aviso: Aviso
    filas: tuple[FilaCamara, ...]
    bandeja: EstadoBandeja
    hogar: Hogar
    pc: DatosPc
    version: str
    pausas: dict[str, str] = field(default_factory=dict)  # clave → «15:00», local time
    en_vivo: dict[str, str] = field(default_factory=dict)  # clave → «10:42», since

    def a_json(self) -> dict[str, Any]:
        """The state for ``ttg.actualizar``."""
        e = self.entradas
        return {
            "screen": "main",
            # False until the first heartbeat answers; the UI shows no transition notices before.
            "listo": e.en_linea is not None,
            "situacion": self.situacion.value,
            "online": e.en_linea is not False,
            "consent": e.consentimiento,
            "retry": e.segundos_para_reintento,
            "linked": e.vinculada,
            "health": asdict(self.aviso),
            "cams": [
                {
                    "id": f.clave,
                    "room": f.habitacion,
                    "device": f.dispositivo,
                    "st": asdict(f.estado),
                    "pause": self.pausas.get(f.clave),
                    "live": self.en_vivo.get(f.clave),
                }
                for f in self.filas
            ],
            "devices": [_webcam_json(w) for w in e.webcams],
            "tray": asdict(self.bandeja),
            "home": {
                "who": self.hogar.nombre_adulto_mayor,
                "first": self.hogar.primer_nombre,
                "addr": self.hogar.direccion,
            },
            "pc": asdict(self.pc),
            "version": self.version,
        }


def _webcam_json(w: Webcam) -> dict[str, Any]:
    return {
        "id": w.clave,
        "name": w.nombre,
        "uid": w.dispositivo_id,
        "room": w.nombre_habitacion,
        "connected": w.conectada,
        "busy": w.ocupada,
        "new": w.nueva,
        "by": w.elegida_desde,
        "preview": w.vista_previa,
    }


# ------------------------------------------------------------------ wording helpers (core.js)

_ARTICULO = {
    "sala": "la sala",
    "dormitorio": "el dormitorio",
    "cocina": "la cocina",
    "comedor": "el comedor",
    "pasillo": "el pasillo",
}
_ARTE = {  # ROOM_ART of proto.js, for the in-window notices
    "sala": "la Sala",
    "dormitorio": "el Dormitorio",
    "cocina": "la Cocina",
    "comedor": "el Comedor",
    "pasillo": "el Pasillo",
}


def de_habitacion(habitacion: str) -> str:
    """``deRoomD``: «la sala», «el dormitorio», or «la habitación «Sala comedor»»."""
    return _ARTICULO.get(habitacion.strip().lower(), f"la habitación «{habitacion}»")


def del_habitacion(habitacion: str) -> str:
    """``delRoom``: «de la sala», «del dormitorio»."""
    texto = de_habitacion(habitacion)
    if texto.startswith("el "):
        return "del " + texto[3:]
    return "de " + texto


def habitacion_arte(habitacion: str) -> str:
    """``ROOM_ART`` of ``proto.js``: «la Sala», «el Dormitorio», «Sala comedor» in quotes."""
    return _ARTE.get(habitacion.strip().lower(), f"«{habitacion}»")


def lista_y(elementos: list[str]) -> str:
    """``listY``: «Sala, Dormitorio y Pasillo»."""
    if len(elementos) < 2:
        return "".join(elementos)
    return ", ".join(elementos[:-1]) + " y " + elementos[-1]


def mayuscula(texto: str) -> str:
    return texto[:1].upper() + texto[1:]


def _mono(texto: str, id_: str | None = None) -> str:
    atributo = f' id="{id_}"' if id_ else ""
    return f'<span class="mono"{atributo}>{escape(texto)}</span>'


def hora_local(instante: datetime, zona: tzinfo | None = None) -> str:
    """«15:00»: the time of day in the PC's time zone (or ``zona``)."""
    return instante.astimezone(zona).strftime("%H:%M")


# ------------------------------------------------------------------ derivation


def situacion(e: Entradas) -> Situacion:
    if e.vinculada and not e.camaras:
        return Situacion.SIN_CAMARAS if not e.webcams_detectadas else Situacion.FALTA_ELEGIR
    if any(not c.webcam_conectada for c in e.camaras):
        return Situacion.WEBCAM_DESCONECTADA
    if e.en_linea is False:
        return Situacion.SIN_INTERNET
    if not e.consentimiento:
        return Situacion.SIN_CONSENTIMIENTO
    if any(c.pausada_hasta is not None for c in e.camaras):
        return Situacion.EN_PAUSA
    if any(c.en_vivo_desde is not None for c in e.camaras):
        return Situacion.EN_VIVO
    return Situacion.CUIDANDO


def _aviso(
    s: Situacion, e: Entradas, hogar: Hogar, pausas: dict[str, str], en_vivo: dict[str, str]
) -> Aviso:
    camaras = list(e.camaras)
    habitaciones = [c.nombre_habitacion for c in camaras]
    ir_a_camaras = Accion("toCams", "Ir a Cámaras", "cam")
    if s is Situacion.SIN_CAMARAS:
        return Aviso(
            "none",
            "none",
            "cam",
            "No encontramos cámaras",
            "Conecta una webcam por USB.",
            ir_a_camaras,
        )
    if s is Situacion.FALTA_ELEGIR:
        n = e.webcams_detectadas or 0
        return Aviso(
            "none",
            "none",
            "mobile",
            "Falta elegir las cámaras en la app",
            f"Detectamos {n} {'cámara' if n == 1 else 'cámaras'}. Mientras tanto, no cuida "
            "ninguna habitación.",
            ir_a_camaras,
        )
    buscar = Accion("rescan", "Buscar de nuevo", "refresh")
    if s is Situacion.WEBCAM_DESCONECTADA:
        perdidas = [c for c in camaras if not c.webcam_conectada]
        funcionan = len(camaras) - len(perdidas)
        titulo = f"{lista_y([c.nombre_habitacion for c in perdidas])} " + (
            "no responde" if len(perdidas) == 1 else "no responden"
        )
        detalle = "Revisa el cable USB" + (
            f" · {funcionan} de {len(camaras)} cámaras funcionan" if len(camaras) > 1 else "."
        )
        return Aviso("warn lost", "off", "videoOff", escape(titulo), escape(detalle), buscar)
    if s is Situacion.SIN_INTERNET:
        return Aviso(
            "offline",
            "off",
            "wifiOff",
            "Sin internet",
            "Las cámaras siguen cuidando; los avisos esperan. Reintento en "
            f"{_mono(str(e.segundos_para_reintento), 'retry')} s.",
            Accion("retryNow", "Reintentar ahora", "refresh"),
        )
    if s is Situacion.SIN_CONSENTIMIENTO:
        return Aviso(
            "warn",
            "consent",
            "doc",
            escape(f"Falta el consentimiento de {hogar.primer_nombre}"),
            "Hasta registrarlo en la app, las cámaras no se usan.",
            None,
        )
    if s is Situacion.EN_PAUSA:
        pausada = min(
            (c for c in camaras if c.pausada_hasta is not None),
            key=lambda c: c.pausada_hasta or datetime.max,
        )
        otras = [c.nombre_habitacion for c in camaras if c.pausada_hasta is None]
        siguen = (
            f"{lista_y(otras)} {'siguen' if len(otras) > 1 else 'sigue'} cuidando · "
            if otras
            else ""
        )
        return Aviso(
            "idle",
            "pause",
            "pause",
            escape(mayuscula(de_habitacion(pausada.nombre_habitacion)))
            + " está en pausa hasta las "
            + _mono(pausas.get(pausada.clave, "")),
            escape(
                siguen + f"la pausó {QUIEN_PAUSA} desde la app"
                if siguen
                else mayuscula(f"la pausó {QUIEN_PAUSA} desde la app")
            ),
            None,
        )
    if s is Situacion.EN_VIVO:
        viendo = next(c for c in camaras if c.en_vivo_desde is not None)
        return Aviso(
            "live",
            "live",
            "eye",
            escape(f"{QUIEN_MIRA} está viendo {de_habitacion(viendo.nombre_habitacion)} en vivo"),
            "Desde las "
            + _mono(en_vivo.get(viendo.clave, ""))
            + " · no se graba · queda registrado",
            None,
        )
    if len(camaras) == 1:
        titulo = f"Te Tengo cuida {de_habitacion(habitaciones[0])}"
    else:
        titulo = f"Te Tengo cuida {len(camaras)} habitaciones"
    return Aviso("ok", "send", "check", escape(titulo), "Todo funciona bien.", None)


def _estado_camara(c: CamaraEntradas, e: Entradas, pausa: str | None) -> EstadoCamara:
    if not c.webcam_conectada:
        return EstadoCamara("off", "Desconectada", "Revisa el cable USB", "videoOff")
    if not e.consentimiento:
        return EstadoCamara("consent", "Detenida", "Falta el consentimiento", "doc")
    if c.pausada_hasta is not None:
        return EstadoCamara("pause", "En pausa", f"Hasta las {_mono(pausa or '')}", "pause")
    if c.en_vivo_desde is not None:
        return EstadoCamara("live", "En vivo", escape(f"{QUIEN_MIRA} mira"), "eye")
    if e.en_linea is False:
        return EstadoCamara("warn", "Sin internet", "Los avisos esperan", "wifiOff")
    return EstadoCamara("send", "En línea", "", "check")


def _bandeja(s: Situacion, e: Entradas, pausas: dict[str, str]) -> EstadoBandeja:
    camaras = e.camaras
    if s in (Situacion.SIN_CAMARAS, Situacion.FALTA_ELEGIR):
        return EstadoBandeja("warn", "falta elegir las cámaras en la app")
    if s is Situacion.WEBCAM_DESCONECTADA:
        return EstadoBandeja("warn", "una cámara no responde")
    if s is Situacion.SIN_INTERNET:
        return EstadoBandeja("warn", "sin internet, reintentando")
    if s is Situacion.SIN_CONSENTIMIENTO:
        return EstadoBandeja("warn", "esperando consentimiento")
    if any(c.en_vivo_desde is not None for c in camaras):
        return EstadoBandeja("live", f"{QUIEN_MIRA} está viendo en vivo")
    pausada = next((c for c in camaras if c.pausada_hasta is not None), None)
    if pausada is not None:
        return EstadoBandeja(
            "idle",
            f"{de_habitacion(pausada.nombre_habitacion)} en pausa hasta las "
            f"{pausas.get(pausada.clave, '')}",
        )
    if len(camaras) == 1:
        return EstadoBandeja("ok", f"cuidando {de_habitacion(camaras[0].nombre_habitacion)}")
    return EstadoBandeja("ok", f"cuidando {len(camaras)} habitaciones")


def derivar(
    e: Entradas, hogar: Hogar, pc: DatosPc, version: str, zona: tzinfo | None = None
) -> EstadoAgente:
    s = situacion(e)
    pausas = {
        c.clave: hora_local(c.pausada_hasta, zona) for c in e.camaras if c.pausada_hasta is not None
    }
    en_vivo = {
        c.clave: hora_local(c.en_vivo_desde, zona) for c in e.camaras if c.en_vivo_desde is not None
    }
    filas = tuple(
        FilaCamara(
            c.clave, c.nombre_habitacion, c.dispositivo, _estado_camara(c, e, pausas.get(c.clave))
        )
        for c in e.camaras
    )
    return EstadoAgente(
        situacion=s,
        entradas=e,
        aviso=_aviso(s, e, hogar, pausas, en_vivo),
        filas=filas,
        bandeja=_bandeja(s, e, pausas),
        hogar=hogar,
        pc=pc,
        version=version,
        pausas=pausas,
        en_vivo=en_vivo,
    )


# ------------------------------------------------------------------ system notifications

_ABRELO = "Ábrelo junto al reloj."


def aviso_al_cerrar(estado: EstadoAgente) -> Notificacion:
    """``osToast(S, 'closed')``: the window was closed or minimized for the first time."""
    s, camaras = estado.situacion, estado.entradas.camaras
    if s in (Situacion.SIN_CAMARAS, Situacion.FALTA_ELEGIR):
        texto = "Falta elegir las cámaras en la app."
    elif s is Situacion.WEBCAM_DESCONECTADA:
        perdida = next(c for c in camaras if not c.webcam_conectada)
        texto = (
            f"La cámara {del_habitacion(perdida.nombre_habitacion)} está desconectada: revisa el "
            "cable USB."
        )
    elif s is Situacion.SIN_INTERNET:
        texto = "Sin internet: las cámaras siguen cuidando."
    elif s is Situacion.SIN_CONSENTIMIENTO:
        texto = "Empieza cuando la familia registre el consentimiento."
    elif s is Situacion.EN_PAUSA:
        pausada = next(c for c in camaras if c.pausada_hasta is not None)
        texto = (
            f"{mayuscula(de_habitacion(pausada.nombre_habitacion))} en pausa hasta las "
            f"{estado.pausas.get(pausada.clave, '')}."
        )
    else:
        cuida = (
            de_habitacion(camaras[0].nombre_habitacion)
            if len(camaras) == 1
            else f"{len(camaras)} habitaciones"
        )
        texto = f"Cuida {cuida}. {_ABRELO}"
    return Notificacion("Sigue funcionando en segundo plano", texto)


def aviso_camara_desconectada(habitacion: str) -> Notificacion:
    """``osToast(S, 'lost')``: a camera stopped answering while the window was closed."""
    return Notificacion(
        f"La cámara {del_habitacion(habitacion)} no responde",
        "Revisa el cable USB.",
    )


def aviso_en_vivo(habitacion: str) -> Notificacion:
    """``osToast(S, 'live')``: someone started watching while the window was closed."""
    return Notificacion(
        f"{QUIEN_MIRA} está viendo {de_habitacion(habitacion)} en vivo",
        "No se graba · queda registrado.",
    )


def aviso_sin_vincular(estado: EstadoAgente | None) -> Notificacion:
    """``osToast(S, 'closed')`` before the cameras run: not linked yet, or none chosen."""
    if estado is not None and estado.entradas.vinculada:
        texto = (
            "Falta elegir las cámaras desde la app Te Tengo, en tu celular. "
            "Esta PC se actualiza sola."
        )
    else:
        texto = "Ábrelo desde su ícono, junto al reloj, para vincular esta PC."
    return Notificacion("Te Tengo Captura sigue funcionando en segundo plano", texto)


def aviso_pc_quitada(hora: str) -> Notificacion:
    """``osToast(S, 'removed')``: the PC was removed from the household in the app (D-31.2)."""
    return Notificacion(
        "Esta PC se quitó de la vivienda",
        f"{QUIEN_PAUSA} la quitó desde la app a las {hora}. Ya no usa las cámaras. "
        "Ábrela para vincularla de nuevo.",
    )
