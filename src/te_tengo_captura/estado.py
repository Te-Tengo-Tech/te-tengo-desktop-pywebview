"""The agent state the window and the tray show: one immutable value, one source of truth.

``derivar`` turns the raw inputs (webcam, internet, consent, pause, last send) into an
``EstadoAgente`` with the priority of ``camState``, ``health`` and ``trayState`` in the prototype
(``docs/references/desktop-prototype/src/core.js``): webcam disconnected › no internet › waiting
for consent › paused › sending. All the Spanish copy of the window, the tray and the system
notifications lives here, copied verbatim from ``core.js`` (see ``docs/BLOCKERS.md``: the
«video» wording is kept until the team updates the prototype). The web UI only renders it.

Fields marked *HTML* are already escaped and may contain the prototype's ``<span class="mono">``;
every other text is plain and the UI escapes it.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, tzinfo
from enum import StrEnum
from html import escape
from typing import Any

from te_tengo_captura.config import Configuracion


class Situacion(StrEnum):
    WEBCAM_DESCONECTADA = "webcam_desconectada"
    SIN_INTERNET = "sin_internet"
    SIN_CONSENTIMIENTO = "sin_consentimiento"
    EN_PAUSA = "en_pausa"
    ENVIANDO = "enviando"


@dataclass(frozen=True, slots=True)
class Entradas:
    webcam_conectada: bool
    en_linea: bool | None  # None before the first heartbeat answers: not shown as offline
    consentimiento: bool
    pausada_hasta: datetime | None
    segundos_desde_envio: int
    segundos_para_reintento: int
    nombre_habitacion: str


@dataclass(frozen=True, slots=True)
class Accion:
    act: str  # data-act of the button: "rescan" or "retryNow"
    texto: str
    clase: str  # btn-secondary or btn-ondark


@dataclass(frozen=True, slots=True)
class EstadoCamara:
    """``camState``: the card of the household camera."""

    k: str
    titulo: str
    detalle_html: str
    icono: str


@dataclass(frozen=True, slots=True)
class Aviso:
    """``health``: the banner at the top of the window."""

    clase: str
    k: str
    icono: str
    titulo_html: str
    detalle: str
    accion: Accion | None


@dataclass(frozen=True, slots=True)
class EstadoBandeja:
    """``trayState``: the dot of the tray icon (ok, idle, warn) and its tooltip."""

    k: str
    etiqueta: str


@dataclass(frozen=True, slots=True)
class Notificacion:
    """``osToast``: a system notification."""

    titulo: str
    texto: str


@dataclass(frozen=True, slots=True)
class EstadoAgente:
    situacion: Situacion
    entradas: Entradas
    pausa: str | None  # «15:00», local time
    camara: EstadoCamara
    aviso: Aviso
    bandeja: EstadoBandeja
    # From the installation file.
    nombre_adulto_mayor: str
    direccion: str
    webcam: str
    especificacion: str
    instalada_el: str
    version: str

    def a_json(self) -> dict[str, Any]:
        """The state for ``ttg.actualizar``: the fields of ``baseState()`` plus the rest."""
        e = self.entradas
        return {
            "screen": "estado",
            "room": e.nombre_habitacion,
            "online": e.en_linea is not False,
            "consent": e.consentimiento,
            "pause": self.pausa,
            "lost": not e.webcam_conectada,
            "retry": e.segundos_para_reintento,
            "ago": e.segundos_desde_envio,
            "toast": None,
            # False until the first heartbeat answers; the UI shows no transition notices before.
            "listo": e.en_linea is not None,
            "situacion": self.situacion.value,
            "cam": asdict(self.camara),
            "health": asdict(self.aviso),
            "tray": asdict(self.bandeja),
            "home": {"who": self.nombre_adulto_mayor, "addr": self.direccion},
            "conf": {
                "webcam": self.webcam,
                "spec": self.especificacion,
                "installed": self.instalada_el,
            },
            "version": self.version,
        }


def _mono(texto: str, id_: str | None = None) -> str:
    atributo = f' id="{id_}"' if id_ else ""
    return f'<span class="mono"{atributo}>{escape(texto)}</span>'


def situacion(e: Entradas) -> Situacion:
    if not e.webcam_conectada:
        return Situacion.WEBCAM_DESCONECTADA
    if e.en_linea is False:
        return Situacion.SIN_INTERNET
    if not e.consentimiento:
        return Situacion.SIN_CONSENTIMIENTO
    if e.pausada_hasta is not None:
        return Situacion.EN_PAUSA
    return Situacion.ENVIANDO


def _camara(s: Situacion, e: Entradas, pausa: str | None) -> EstadoCamara:
    if s is Situacion.WEBCAM_DESCONECTADA:
        return EstadoCamara(
            "off", "Sin conexión", "Webcam desconectada: revisa el cable USB", "videoOff"
        )
    if s is Situacion.SIN_INTERNET:
        return EstadoCamara("off", "Sin conexión", "Esperando internet", "wifiOff")
    if s is Situacion.SIN_CONSENTIMIENTO:
        return EstadoCamara("consent", "Esperando consentimiento", "No se envía video", "doc")
    if s is Situacion.EN_PAUSA:
        return EstadoCamara(
            "pause", "En pausa", f"Hasta las {_mono(pausa or '')} · desde la app", "pause"
        )
    return EstadoCamara("send", "Enviando", f"Hace {e.segundos_desde_envio} s", "upload")


def _aviso(s: Situacion, e: Entradas, pausa: str | None, c: Configuracion) -> Aviso:
    if s is Situacion.WEBCAM_DESCONECTADA:
        return Aviso(
            "warn lost",
            "off",
            "videoOff",
            "Webcam desconectada: revisa el cable USB",
            f"Dejamos de recibir imagen de la {c.webcam.nombre}. Conéctala de nuevo al mismo "
            "puerto USB; el envío se reanuda solo.",
            Accion("rescan", "Buscar de nuevo", "btn-secondary"),
        )
    if s is Situacion.SIN_INTERNET:
        return Aviso(
            "dark",
            "off",
            "wifiOff",
            f"Sin internet · reintentando en {_mono(str(e.segundos_para_reintento), 'retry')} s",
            "La webcam sigue conectada a esta PC. El envío se reanuda solo cuando vuelva la "
            "conexión.",
            Accion("retryNow", "Reintentar ahora", "btn-ondark"),
        )
    if s is Situacion.SIN_CONSENTIMIENTO:
        nombre = c.vivienda.nombre_adulto_mayor.split(" ")[0]
        return Aviso(
            "warn",
            "consent",
            "doc",
            "Esperando consentimiento",
            "La cámara no envía video hasta que la familia registre el consentimiento de "
            f"{nombre} en la app Te Tengo.",
            None,
        )
    if s is Situacion.EN_PAUSA:
        return Aviso(
            "idle",
            "pause",
            "pause",
            f"En pausa hasta las {_mono(pausa or '')}",
            "La familia pausó la cámara desde la app Te Tengo. El envío se reanuda solo a esa "
            "hora.",
            None,
        )
    return Aviso(
        "ok",
        "send",
        "upload",
        "Enviando video · conectado",
        f"Video cifrado · último envío hace {e.segundos_desde_envio} s",
        None,
    )


def _bandeja(s: Situacion, e: Entradas, pausa: str | None) -> EstadoBandeja:
    if s is Situacion.WEBCAM_DESCONECTADA:
        return EstadoBandeja("warn", "webcam desconectada")
    if s is Situacion.SIN_INTERNET:
        return EstadoBandeja("warn", "sin internet, reintentando")
    if s is Situacion.SIN_CONSENTIMIENTO:
        return EstadoBandeja("warn", "esperando consentimiento")
    if s is Situacion.EN_PAUSA:
        return EstadoBandeja("idle", f"en pausa hasta las {pausa}")
    sala = "de la sala" if e.nombre_habitacion == "Sala" else f"de {e.nombre_habitacion}"
    return EstadoBandeja("ok", f"enviando video de la cámara {sala}")


def hora_local(instante: datetime, zona: tzinfo | None = None) -> str:
    """«15:00»: the time of day in the PC's time zone (or ``zona``)."""
    return instante.astimezone(zona).strftime("%H:%M")


def derivar(
    e: Entradas, config: Configuracion, version: str, zona: tzinfo | None = None
) -> EstadoAgente:
    s = situacion(e)
    pausa = hora_local(e.pausada_hasta, zona) if e.pausada_hasta is not None else None
    return EstadoAgente(
        situacion=s,
        entradas=e,
        pausa=pausa,
        camara=_camara(s, e, pausa),
        aviso=_aviso(s, e, pausa, config),
        bandeja=_bandeja(s, e, pausa),
        nombre_adulto_mayor=config.vivienda.nombre_adulto_mayor,
        direccion=config.vivienda.direccion,
        webcam=config.webcam.nombre,
        especificacion=config.webcam.especificacion,
        instalada_el=config.instalada_el.strftime("%d/%m/%Y"),
        version=version,
    )


# ------------------------------------------------------------------ system notifications


def aviso_al_cerrar(estado: EstadoAgente) -> Notificacion:
    """``osToast(S, 'closed')``: the window was closed or minimized for the first time."""
    s = estado.situacion
    if s is Situacion.WEBCAM_DESCONECTADA:
        texto = (
            "La webcam está desconectada: revisa el cable USB. "
            "Ábrelo desde su ícono, junto al reloj."
        )
    elif s is Situacion.SIN_INTERNET:
        texto = "Seguirá intentando conectarse a internet. Ábrelo desde su ícono, junto al reloj."
    elif s is Situacion.SIN_CONSENTIMIENTO:
        texto = "Empezará a enviar cuando la familia complete el consentimiento en la app Te Tengo."
    elif s is Situacion.EN_PAUSA:
        texto = (
            f"La cámara está en pausa hasta las {estado.pausa}. "
            "Ábrelo desde su ícono, junto al reloj."
        )
    else:
        texto = "Sigue enviando el video de la cámara. Ábrelo desde su ícono, junto al reloj."
    return Notificacion("Te Tengo Captura sigue funcionando en segundo plano", texto)


def aviso_webcam_desconectada(config: Configuracion) -> Notificacion:
    """``osToast(S, 'lost')``: the webcam was disconnected while the window was closed."""
    return Notificacion(
        "La webcam se desconectó",
        f"Revisa que el cable USB de la {config.webcam.nombre} esté bien conectado. "
        "Mientras tanto no se envía video.",
    )
