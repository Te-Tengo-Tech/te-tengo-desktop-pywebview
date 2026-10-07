from datetime import UTC, datetime, timedelta, timezone

import pytest

from te_tengo_captura.config import Configuracion
from te_tengo_captura.estado import (
    Entradas,
    Situacion,
    aviso_al_cerrar,
    aviso_webcam_desconectada,
    derivar,
    hora_local,
)

LIMA = timezone(timedelta(hours=-5))
PAUSA = datetime(2026, 10, 7, 20, 0, tzinfo=UTC)  # 15:00 in Lima


def entradas(**cambios: object) -> Entradas:
    base: dict[str, object] = {
        "webcam_conectada": True,
        "en_linea": True,
        "consentimiento": True,
        "pausada_hasta": None,
        "segundos_desde_envio": 2,
        "segundos_para_reintento": 8,
        "nombre_habitacion": "Sala",
    }
    return Entradas(**{**base, **cambios})  # type: ignore[arg-type]


# The five states of the prototype (screens 01–05) and their priority.
@pytest.mark.parametrize(
    ("cambios", "situacion"),
    [
        ({}, Situacion.ENVIANDO),
        ({"pausada_hasta": PAUSA}, Situacion.EN_PAUSA),
        ({"consentimiento": False}, Situacion.SIN_CONSENTIMIENTO),
        ({"en_linea": False}, Situacion.SIN_INTERNET),
        ({"webcam_conectada": False}, Situacion.WEBCAM_DESCONECTADA),
        # Priority: lost › offline › consent › pause › sending.
        ({"webcam_conectada": False, "en_linea": False}, Situacion.WEBCAM_DESCONECTADA),
        ({"en_linea": False, "consentimiento": False}, Situacion.SIN_INTERNET),
        ({"consentimiento": False, "pausada_hasta": PAUSA}, Situacion.SIN_CONSENTIMIENTO),
        ({"en_linea": False, "pausada_hasta": PAUSA}, Situacion.SIN_INTERNET),
        ({"webcam_conectada": False, "pausada_hasta": PAUSA}, Situacion.WEBCAM_DESCONECTADA),
        # Before the first heartbeat answers, the agent is not shown as offline.
        ({"en_linea": None}, Situacion.ENVIANDO),
    ],
)
def test_prioridad(
    configuracion: Configuracion, cambios: dict[str, object], situacion: Situacion
) -> None:
    assert derivar(entradas(**cambios), configuracion, "1.0", LIMA).situacion is situacion


# Texts verbatim from camState, health and trayState in core.js.
@pytest.mark.parametrize(
    ("cambios", "camara", "aviso", "bandeja"),
    [
        (
            {},
            ("send", "Enviando", "Hace 2 s", "upload"),
            (
                "ok",
                "send",
                "Enviando video · conectado",
                "Video cifrado · último envío hace 2 s",
                None,
            ),
            ("ok", "enviando video de la cámara de la sala"),
        ),
        (
            {"pausada_hasta": PAUSA},
            (
                "pause",
                "En pausa",
                'Hasta las <span class="mono">15:00</span> · desde la app',
                "pause",
            ),
            (
                "idle",
                "pause",
                'En pausa hasta las <span class="mono">15:00</span>',
                "La familia pausó la cámara desde la app Te Tengo. El envío se reanuda solo a esa hora.",
                None,
            ),
            ("idle", "en pausa hasta las 15:00"),
        ),
        (
            {"consentimiento": False},
            ("consent", "Esperando consentimiento", "No se envía video", "doc"),
            (
                "warn",
                "consent",
                "Esperando consentimiento",
                "La cámara no envía video hasta que la familia registre el consentimiento de Rosa en la app Te Tengo.",
                None,
            ),
            ("warn", "esperando consentimiento"),
        ),
        (
            {"en_linea": False},
            ("off", "Sin conexión", "Esperando internet", "wifiOff"),
            (
                "dark",
                "off",
                'Sin internet · reintentando en <span class="mono" id="retry">8</span> s',
                "La webcam sigue conectada a esta PC. El envío se reanuda solo cuando vuelva la conexión.",
                ("retryNow", "Reintentar ahora", "btn-ondark"),
            ),
            ("warn", "sin internet, reintentando"),
        ),
        (
            {"webcam_conectada": False},
            ("off", "Sin conexión", "Webcam desconectada: revisa el cable USB", "videoOff"),
            (
                "warn lost",
                "off",
                "Webcam desconectada: revisa el cable USB",
                "Dejamos de recibir imagen de la Webcam USB HD (1080p). Conéctala de nuevo al mismo puerto USB; el envío se reanuda solo.",
                ("rescan", "Buscar de nuevo", "btn-secondary"),
            ),
            ("warn", "webcam desconectada"),
        ),
    ],
)
def test_textos_del_prototipo(
    configuracion: Configuracion,
    cambios: dict[str, object],
    camara: tuple[str, str, str, str],
    aviso: tuple[str, str, str, str, tuple[str, str, str] | None],
    bandeja: tuple[str, str],
) -> None:
    estado = derivar(entradas(**cambios), configuracion, "1.0", LIMA)
    c, a, b = estado.camara, estado.aviso, estado.bandeja
    assert (c.k, c.titulo, c.detalle_html, c.icono) == camara
    accion = (a.accion.act, a.accion.texto, a.accion.clase) if a.accion else None
    assert (a.clase, a.k, a.titulo_html, a.detalle, accion) == aviso
    assert (b.k, b.etiqueta) == bandeja


def test_bandeja_con_otra_habitacion(configuracion: Configuracion) -> None:
    estado = derivar(entradas(nombre_habitacion="Dormitorio"), configuracion, "1.0", LIMA)
    assert estado.bandeja.etiqueta == "enviando video de la cámara de Dormitorio"


def test_la_hora_de_la_pausa_se_escapa(configuracion: Configuracion) -> None:
    assert hora_local(PAUSA, LIMA) == "15:00"
    estado = derivar(entradas(pausada_hasta=PAUSA), configuracion, "1.0", LIMA)
    assert estado.pausa == "15:00"


def test_json_para_la_interfaz(configuracion: Configuracion) -> None:
    datos = derivar(entradas(en_linea=False), configuracion, "1.0.0", LIMA).a_json()
    # The fields of baseState() in core.js…
    assert {
        k: datos[k]
        for k in ("screen", "room", "online", "consent", "pause", "lost", "retry", "ago", "toast")
    } == {
        "screen": "estado",
        "room": "Sala",
        "online": False,
        "consent": True,
        "pause": None,
        "lost": False,
        "retry": 8,
        "ago": 2,
        "toast": None,
    }
    # …plus the household and the webcam from the installation file.
    assert datos["home"] == {"who": "Rosa Huamán", "addr": "Jr. Los Pinos 482, San Miguel, Lima"}
    assert datos["conf"] == {
        "webcam": "Webcam USB HD (1080p)",
        "spec": "USB · 1920 × 1080",
        "installed": "22/09/2026",
    }
    assert datos["situacion"] == "sin_internet"
    assert datos["listo"] is True
    assert datos["health"]["accion"] == {
        "act": "retryNow",
        "texto": "Reintentar ahora",
        "clase": "btn-ondark",
    }
    assert datos["tray"] == {"k": "warn", "etiqueta": "sin internet, reintentando"}
    assert datos["version"] == "1.0.0"


@pytest.mark.parametrize(
    ("cambios", "texto"),
    [
        ({}, "Sigue enviando el video de la cámara. Ábrelo desde su ícono, junto al reloj."),
        (
            {"pausada_hasta": PAUSA},
            "La cámara está en pausa hasta las 15:00. Ábrelo desde su ícono, junto al reloj.",
        ),
        (
            {"consentimiento": False},
            "Empezará a enviar cuando la familia complete el consentimiento en la app Te Tengo.",
        ),
        (
            {"en_linea": False},
            "Seguirá intentando conectarse a internet. Ábrelo desde su ícono, junto al reloj.",
        ),
        (
            {"webcam_conectada": False},
            "La webcam está desconectada: revisa el cable USB. Ábrelo desde su ícono, junto al reloj.",
        ),
    ],
)
def test_aviso_al_cerrar(
    configuracion: Configuracion, cambios: dict[str, object], texto: str
) -> None:
    aviso = aviso_al_cerrar(derivar(entradas(**cambios), configuracion, "1.0", LIMA))
    assert aviso.titulo == "Te Tengo Captura sigue funcionando en segundo plano"
    assert aviso.texto == texto


def test_aviso_webcam_desconectada(configuracion: Configuracion) -> None:
    aviso = aviso_webcam_desconectada(configuracion)
    assert aviso.titulo == "La webcam se desconectó"
    assert aviso.texto == (
        "Revisa que el cable USB de la Webcam USB HD (1080p) esté bien conectado. "
        "Mientras tanto no se envía video."
    )


def test_estado_inmutable(configuracion: Configuracion) -> None:
    estado = derivar(entradas(), configuracion, "1.0", LIMA)
    with pytest.raises(AttributeError):
        estado.situacion = Situacion.EN_PAUSA  # type: ignore[misc]
