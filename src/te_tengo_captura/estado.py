"""The agent state the window and the tray show: one immutable value, one source of truth.

``derivar`` turns the raw inputs (the cameras of this PC, internet, consent, pauses, live view)
into an ``EstadoAgente`` with the priorities of ``health``, ``camStatus`` and ``trayState`` in the
desktop prototype (docs repo ``05-prototipos/app-escritorio/.impeccable/src/core.js``, copied to
``docs/references/desktop-prototype/src/core.js``):

* the summary (``health``): no webcam found › cameras not chosen yet › a camera does not answer ›
  no internet › no consent › a camera paused › someone watching live › all good;
* each camera's row (``camStatus``): disconnected › no consent › paused › live › no internet ›
  online;
* the tray dot (``trayState``): someone previews a webcam to choose it › not linked › cameras not
  chosen › a camera lost › offline › no consent › live › paused › all good.

All the copy that depends on the state lives here, in the current language (``i18n``): the
Spanish is copied verbatim from ``core.js`` (UI term «habitación»); where the prototype has no
sentence for a case the agent can reach (several cameras lost or paused, nobody named as the
viewer) the closest prototype sentence is adapted and listed in ``docs/BLOCKERS.md``. The web UI
only renders it. Fields named ``*_html``
are already escaped and may contain the prototype's ``<span class="mono">``; every other text is
plain and the UI escapes it.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, tzinfo
from enum import StrEnum
from html import escape
from typing import Any, Protocol

from te_tengo_captura import i18n
from te_tengo_captura.i18n import t


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
    fps: float | None = None  # the real rate of analysed frames (several cameras per PC)


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
    mirando: bool = False  # a family member previews it from the app to choose it (CA-29.7)
    esqueleto: bool = False  # in use: its preview can draw the live pose («Qué se ve»)


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
class Ayuda:
    """A help behind a «?» icon (core.js ``infoTip``): text, topic of its button, key."""

    texto: str
    tema: str
    clave: str


def ayuda_en_vivo() -> Ayuda:
    """core.js health: the live view's privacy note, moved from the summary's detail into the
    «?» icon."""
    return Ayuda(t("ayuda.en_vivo"), t("ayuda.en_vivo.tema"), "health-live")


@dataclass(frozen=True, slots=True)
class Aviso:
    """``health``: the summary block at the top of «Estado»."""

    clase: str
    k: str
    icono: str
    titulo_html: str
    detalle_html: str
    accion: Accion | None
    ayuda: Ayuda | None = None


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
    fps: float | None = None
    elegida_desde: str | None = None


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
    idioma: str = i18n.PREDETERMINADO  # the language of every text above (``i18n``)

    def a_json(self) -> dict[str, Any]:
        """The state for ``ttg.actualizar``."""
        e = self.entradas
        return {
            "screen": "main",
            "idioma": self.idioma,
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
                    "fps": round(f.fps, 1) if f.fps is not None else None,
                    "by": f.elegida_desde,
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
        "peek": w.mirando,
        "skel": w.esqueleto,
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


def _es(idioma_: str | None) -> bool:
    return (idioma_ or i18n.idioma()) == i18n.ES


def de_habitacion(habitacion: str, idioma_: str | None = None) -> str:
    """``deRoomD``: «la sala», «el dormitorio», or «la habitación «Sala comedor»». In English the
    room's name as the family wrote it."""
    if not _es(idioma_):
        return habitacion
    return _ARTICULO.get(habitacion.strip().lower(), f"la habitación «{habitacion}»")


def del_habitacion(habitacion: str, idioma_: str | None = None) -> str:
    """``delRoom``: «de la sala», «del dormitorio» (English: the room's name)."""
    texto = de_habitacion(habitacion, idioma_)
    if not _es(idioma_):
        return texto
    if texto.startswith("el "):
        return "del " + texto[3:]
    return "de " + texto


def habitacion_arte(habitacion: str, idioma_: str | None = None) -> str:
    """``ROOM_ART`` of ``proto.js``: «la Sala», «el Dormitorio», «Sala comedor» in quotes
    (English: the room's name)."""
    if not _es(idioma_):
        return habitacion
    return _ARTE.get(habitacion.strip().lower(), f"«{habitacion}»")


def lista_y(elementos: list[str], idioma_: str | None = None) -> str:
    """``listY``: «Sala, Dormitorio y Pasillo» («Sala, Dormitorio and Pasillo» in English)."""
    if len(elementos) < 2:
        return "".join(elementos)
    y = i18n.traducir(idioma_ or i18n.idioma(), "lista.y")
    return ", ".join(elementos[:-1]) + f" {y} " + elementos[-1]


def mayuscula(texto: str) -> str:
    return texto[:1].upper() + texto[1:]


def plural(clave: str, n: int, **valores: object) -> str:
    """``clave.uno`` for one, ``clave.otros`` otherwise."""
    return t(f"{clave}.{'uno' if n == 1 else 'otros'}", n=n, **valores)


def quien_mira() -> str:
    """core.js osToast fallback: the contract does not say who watches («Un familiar»)."""
    return t("quien.familiar")


def quien_pausa() -> str:
    """core.js health fallback (``S.pauseBy||'la familia'``)."""
    return t("quien.familia")


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
    ir_a_camaras = Accion("toCams", t("accion.ir_a_camaras"), "cam")
    if s is Situacion.SIN_CAMARAS:
        return Aviso(
            "none",
            "none",
            "cam",
            t("aviso.sin_camaras.titulo"),
            t("aviso.sin_camaras.detalle"),
            ir_a_camaras,
        )
    if s is Situacion.FALTA_ELEGIR:
        n = e.webcams_detectadas or 0
        return Aviso(
            "none",
            "none",
            "mobile",
            t("aviso.falta_elegir.titulo"),
            plural("aviso.falta_elegir.detalle", n),
            ir_a_camaras,
        )
    buscar = Accion("rescan", t("accion.buscar_de_nuevo"), "refresh")
    if s is Situacion.WEBCAM_DESCONECTADA:
        perdidas = [c for c in camaras if not c.webcam_conectada]
        funcionan = len(camaras) - len(perdidas)
        titulo = plural(
            "aviso.desconectada.titulo",
            len(perdidas),
            salas=lista_y([c.nombre_habitacion for c in perdidas]),
        )
        detalle = (
            t("aviso.desconectada.detalle_varias", funcionan=funcionan, total=len(camaras))
            if len(camaras) > 1
            else t("aviso.desconectada.detalle")
        )
        return Aviso("warn lost", "off", "videoOff", escape(titulo), escape(detalle), buscar)
    if s is Situacion.SIN_INTERNET:
        return Aviso(
            "offline",
            "off",
            "wifiOff",
            t("aviso.sin_internet.titulo"),
            t(
                "aviso.sin_internet.detalle",
                segundos=_mono(str(e.segundos_para_reintento), "retry"),
            ),
            Accion("retryNow", t("accion.reintentar_ahora"), "refresh"),
        )
    if s is Situacion.SIN_CONSENTIMIENTO:
        return Aviso(
            "warn",
            "consent",
            "doc",
            escape(t("aviso.consentimiento.titulo", nombre=hogar.primer_nombre)),
            t("aviso.consentimiento.detalle"),
            None,
        )
    if s is Situacion.EN_PAUSA:
        pausada = min(
            (c for c in camaras if c.pausada_hasta is not None),
            key=lambda c: c.pausada_hasta or datetime.max,
        )
        otras = [c.nombre_habitacion for c in camaras if c.pausada_hasta is None]
        siguen = plural("aviso.pausa.siguen", len(otras), salas=lista_y(otras)) if otras else ""
        pauso = t("aviso.pausa.pauso", quien=quien_pausa())
        return Aviso(
            "idle",
            "pause",
            "pause",
            t(
                "aviso.pausa.titulo",
                sala=escape(mayuscula(de_habitacion(pausada.nombre_habitacion))),
                hora=_mono(pausas.get(pausada.clave, "")),
            ),
            escape(siguen + pauso if siguen else mayuscula(pauso)),
            None,
        )
    if s is Situacion.EN_VIVO:
        viendo = next(c for c in camaras if c.en_vivo_desde is not None)
        return Aviso(
            "live",
            "live",
            "eye",
            escape(
                t(
                    "aviso.en_vivo.titulo",
                    quien=quien_mira(),
                    sala=de_habitacion(viendo.nombre_habitacion),
                )
            ),
            t("aviso.en_vivo.detalle", hora=_mono(en_vivo.get(viendo.clave, ""))),
            None,
            ayuda_en_vivo(),
        )
    if len(camaras) == 1:
        titulo = t("aviso.cuida.una", sala=de_habitacion(habitaciones[0]))
    else:
        titulo = t("aviso.cuida.varias", n=len(camaras))
    return Aviso("ok", "send", "check", escape(titulo), t("aviso.cuida.detalle"), None)


def _estado_camara(c: CamaraEntradas, e: Entradas, pausa: str | None) -> EstadoCamara:
    if not c.webcam_conectada:
        return EstadoCamara(
            "off", t("camara.desconectada"), t("camara.desconectada.detalle"), "videoOff"
        )
    if not e.consentimiento:
        return EstadoCamara("consent", t("camara.detenida"), t("camara.detenida.detalle"), "doc")
    if c.pausada_hasta is not None:
        return EstadoCamara(
            "pause",
            t("camara.en_pausa"),
            t("camara.en_pausa.detalle", hora=_mono(pausa or "")),
            "pause",
        )
    if c.en_vivo_desde is not None:
        return EstadoCamara(
            "live",
            t("camara.en_vivo"),
            escape(t("camara.en_vivo.detalle", quien=quien_mira())),
            "eye",
        )
    if e.en_linea is False:
        return EstadoCamara(
            "warn", t("camara.sin_internet"), t("camara.sin_internet.detalle"), "wifiOff"
        )
    return EstadoCamara("send", t("camara.en_linea"), "", "check")


def _bandeja(s: Situacion, e: Entradas, pausas: dict[str, str]) -> EstadoBandeja:
    camaras = e.camaras
    if any(w.mirando for w in e.webcams):
        return EstadoBandeja("live", t("bandeja.mira_para_elegir", quien=quien_mira()))
    if s in (Situacion.SIN_CAMARAS, Situacion.FALTA_ELEGIR):
        return EstadoBandeja("warn", t("bandeja.falta_elegir"))
    if s is Situacion.WEBCAM_DESCONECTADA:
        return EstadoBandeja("warn", t("bandeja.no_responde"))
    if s is Situacion.SIN_INTERNET:
        return EstadoBandeja("warn", t("bandeja.sin_internet"))
    if s is Situacion.SIN_CONSENTIMIENTO:
        return EstadoBandeja("warn", t("bandeja.esperando_consentimiento"))
    if any(c.en_vivo_desde is not None for c in camaras):
        return EstadoBandeja("live", t("bandeja.en_vivo", quien=quien_mira()))
    pausada = next((c for c in camaras if c.pausada_hasta is not None), None)
    if pausada is not None:
        return EstadoBandeja(
            "idle",
            t(
                "bandeja.en_pausa",
                sala=de_habitacion(pausada.nombre_habitacion),
                hora=pausas.get(pausada.clave, ""),
            ),
        )
    if len(camaras) == 1:
        return EstadoBandeja(
            "ok", t("bandeja.cuidando.una", sala=de_habitacion(camaras[0].nombre_habitacion))
        )
    return EstadoBandeja("ok", t("bandeja.cuidando.varias", n=len(camaras)))


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
            c.clave,
            c.nombre_habitacion,
            c.dispositivo,
            _estado_camara(c, e, pausas.get(c.clave)),
            c.fps,
            c.elegida_desde,
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
        idioma=i18n.idioma(),
    )


# ------------------------------------------------------------------ system notifications


def aviso_al_cerrar(estado: EstadoAgente) -> Notificacion:
    """``osToast(S, 'closed')``: the window was closed or minimized for the first time."""
    s, camaras = estado.situacion, estado.entradas.camaras
    if s in (Situacion.SIN_CAMARAS, Situacion.FALTA_ELEGIR):
        texto = t("notificacion.falta_elegir")
    elif s is Situacion.WEBCAM_DESCONECTADA:
        perdida = next(c for c in camaras if not c.webcam_conectada)
        texto = t("notificacion.desconectada", sala=del_habitacion(perdida.nombre_habitacion))
    elif s is Situacion.SIN_INTERNET:
        texto = t("notificacion.sin_internet")
    elif s is Situacion.SIN_CONSENTIMIENTO:
        texto = t("notificacion.sin_consentimiento")
    elif s is Situacion.EN_PAUSA:
        pausada = next(c for c in camaras if c.pausada_hasta is not None)
        texto = t(
            "notificacion.en_pausa",
            sala=mayuscula(de_habitacion(pausada.nombre_habitacion)),
            hora=estado.pausas.get(pausada.clave, ""),
        )
    else:
        cuida = (
            de_habitacion(camaras[0].nombre_habitacion)
            if len(camaras) == 1
            else t("habitaciones", n=len(camaras))
        )
        texto = t("notificacion.cuida", cuida=cuida)
    return Notificacion(t("notificacion.segundo_plano"), texto)


def aviso_camara_desconectada(habitacion: str) -> Notificacion:
    """``osToast(S, 'lost')``: a camera stopped answering while the window was closed."""
    return Notificacion(
        t("notificacion.no_responde", sala=del_habitacion(habitacion)),
        t("notificacion.no_responde.detalle"),
    )


def aviso_en_vivo(habitacion: str) -> Notificacion:
    """``osToast(S, 'live')``: someone started watching while the window was closed."""
    return Notificacion(
        t("aviso.en_vivo.titulo", quien=quien_mira(), sala=de_habitacion(habitacion)),
        t("notificacion.en_vivo.detalle"),
    )


def aviso_sin_vincular(estado: EstadoAgente | None) -> Notificacion:
    """``osToast(S, 'closed')`` before the cameras run: not linked yet, or none chosen."""
    if estado is not None and estado.entradas.vinculada:
        texto = t("notificacion.falta_elegir")
    else:
        texto = t("notificacion.sin_vincular")
    return Notificacion(t("notificacion.segundo_plano"), texto)


def aviso_version_nueva(version: str, mac: bool = False) -> Notificacion:
    """``osToast(S, 'update')`` (screen 67, US-43): one notice per new version."""
    return Notificacion(
        t("notificacion.version_nueva", version=version),
        t("notificacion.version_nueva.mac" if mac else "notificacion.version_nueva.windows"),
    )


def aviso_pc_quitada(hora: str) -> Notificacion:
    """``osToast(S, 'removed')``: the PC was removed from the household in the app (D-31.2)."""
    return Notificacion(
        t("notificacion.quitada"),
        t("notificacion.quitada.detalle", quien=mayuscula(quien_pausa()), hora=hora),
    )
