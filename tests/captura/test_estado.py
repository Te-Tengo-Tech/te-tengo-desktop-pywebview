from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest

from te_tengo_captura.estado import (
    Situacion,
    aviso_al_cerrar,
    aviso_camara_desconectada,
    aviso_en_vivo,
    de_habitacion,
    del_habitacion,
    habitacion_arte,
    hora_local,
    lista_y,
)
from tests.captura.estados import PC, camara, estado

LIMA = timezone(timedelta(hours=-5))
PAUSA = datetime(2026, 9, 23, 16, 42, tzinfo=UTC)  # 11:42 in Lima
VIVO = datetime(2026, 9, 23, 15, 42, tzinfo=UTC)  # 10:42 in Lima
TRES = (camara("Sala"), camara("Dormitorio"), camara("Pasillo"))


@pytest.mark.parametrize(
    ("camaras", "cambios", "situacion"),
    [
        ((camara(),), {}, Situacion.CUIDANDO),
        ((camara(pausada_hasta=PAUSA),), {}, Situacion.EN_PAUSA),
        ((camara(en_vivo_desde=VIVO),), {}, Situacion.EN_VIVO),
        ((camara(),), {"consentimiento": False}, Situacion.SIN_CONSENTIMIENTO),
        ((camara(),), {"en_linea": False}, Situacion.SIN_INTERNET),
        ((camara(webcam_conectada=False),), {}, Situacion.WEBCAM_DESCONECTADA),
        # Priority (health): lost › offline › consent › pause › live › caring.
        ((camara(webcam_conectada=False),), {"en_linea": False}, Situacion.WEBCAM_DESCONECTADA),
        ((camara(),), {"en_linea": False, "consentimiento": False}, Situacion.SIN_INTERNET),
        ((camara(pausada_hasta=PAUSA),), {"consentimiento": False}, Situacion.SIN_CONSENTIMIENTO),
        ((camara(pausada_hasta=PAUSA, en_vivo_desde=VIVO),), {}, Situacion.EN_PAUSA),
        # Before the first heartbeat answers, the agent is not shown as offline.
        ((camara(),), {"en_linea": None}, Situacion.CUIDANDO),
        # A linked PC with no camera in use.
        ((), {"vinculada": True, "webcams_detectadas": 0, "webcams": ()}, Situacion.SIN_CAMARAS),
        ((), {"vinculada": True, "webcams_detectadas": 3, "webcams": ()}, Situacion.FALTA_ELEGIR),
    ],
)
def test_prioridad(camaras: tuple, cambios: dict[str, Any], situacion: Situacion) -> None:  # type: ignore[type-arg]
    if not camaras:
        from te_tengo_captura.estado import DatosPc, Entradas, derivar
        from tests.captura.estados import HOGAR

        e = Entradas((), True, True, 8, **cambios)
        assert derivar(e, HOGAR, DatosPc("PC", "x", "y"), "1").situacion is situacion
        return
    assert estado(*camaras, **cambios).situacion is situacion


# Texts verbatim from health, camStatus and trayState in core.js.
@pytest.mark.parametrize(
    ("camaras", "cambios", "aviso", "fila", "bandeja"),
    [
        (
            (camara(),),
            {},
            ("ok", "send", "check", "Te Tengo cuida la sala", "Todo funciona bien.", None),
            ("send", "En línea", "", "check"),
            ("ok", "cuidando la sala"),
        ),
        (
            TRES,
            {},
            (
                "ok",
                "send",
                "check",
                "Te Tengo cuida 3 habitaciones",
                "Todo funciona bien.",
                None,
            ),
            ("send", "En línea", "", "check"),
            ("ok", "cuidando 3 habitaciones"),
        ),
        (
            (camara(), camara("Dormitorio"), camara("Pasillo", webcam_conectada=False)),
            {},
            (
                "warn lost",
                "off",
                "videoOff",
                "Pasillo no responde",
                "Revisa el cable USB · 2 de 3 cámaras funcionan",
                ("rescan", "Buscar de nuevo", "refresh"),
            ),
            ("send", "En línea", "", "check"),
            ("warn", "una cámara no responde"),
        ),
        (
            (camara(webcam_conectada=False),),
            {},
            (
                "warn lost",
                "off",
                "videoOff",
                "Sala no responde",
                "Revisa el cable USB.",
                ("rescan", "Buscar de nuevo", "refresh"),
            ),
            ("off", "Desconectada", "Revisa el cable USB", "videoOff"),
            ("warn", "una cámara no responde"),
        ),
        (
            (camara(),),
            {"en_linea": False},
            (
                "offline",
                "off",
                "wifiOff",
                "Sin internet",
                'Las cámaras siguen cuidando; los avisos esperan. Reintento en <span class="mono" id="retry">8</span> s.',
                ("retryNow", "Reintentar ahora", "refresh"),
            ),
            ("warn", "Sin internet", "Los avisos esperan", "wifiOff"),
            ("warn", "sin internet, reintentando"),
        ),
        (
            (camara(),),
            {"consentimiento": False},
            (
                "warn",
                "consent",
                "doc",
                "Falta el consentimiento de Rosa",
                "Hasta registrarlo en la app, las cámaras no se usan.",
                None,
            ),
            ("consent", "Detenida", "Falta el consentimiento", "doc"),
            ("warn", "esperando consentimiento"),
        ),
        (
            (camara(pausada_hasta=PAUSA), camara("Dormitorio"), camara("Pasillo")),
            {},
            (
                "idle",
                "pause",
                "pause",
                'La sala está en pausa hasta las <span class="mono">11:42</span>',
                "Dormitorio y Pasillo siguen cuidando · la pausó la familia desde la app",
                None,
            ),
            ("pause", "En pausa", 'Hasta las <span class="mono">11:42</span>', "pause"),
            ("idle", "la sala en pausa hasta las 11:42"),
        ),
        (
            (camara(en_vivo_desde=VIVO),),
            {},
            (
                "live",
                "live",
                "eye",
                "Un familiar está viendo la sala en vivo",
                'Desde las <span class="mono">10:42</span>',
                None,
            ),
            ("live", "En vivo", "Un familiar mira", "eye"),
            ("live", "Un familiar está viendo en vivo"),
        ),
    ],
)
def test_textos_del_prototipo(
    camaras: tuple,  # type: ignore[type-arg]
    cambios: dict[str, Any],
    aviso: tuple[str, str, str, str, str, tuple[str, str, str] | None],
    fila: tuple[str, str, str, str],
    bandeja: tuple[str, str],
) -> None:
    e = estado(*camaras, zona=LIMA, **cambios)
    a, f, b = e.aviso, e.filas[0].estado, e.bandeja
    accion = (a.accion.act, a.accion.texto, a.accion.icono) if a.accion else None
    assert (a.clase, a.k, a.icono, a.titulo_html, a.detalle_html, accion) == aviso
    assert (f.k, f.titulo, f.detalle_html, f.icono) == fila
    assert (b.k, b.etiqueta) == bandeja


def test_la_privacidad_de_la_vista_en_vivo_va_en_el_icono_de_ayuda() -> None:
    """core.js health: «no se graba · queda registrado» moved from the detail into a «?» icon."""
    vivo = estado(camara(en_vivo_desde=VIVO), zona=LIMA)
    assert vivo.aviso.ayuda is not None
    assert (vivo.aviso.ayuda.texto, vivo.aviso.ayuda.tema, vivo.aviso.ayuda.clave) == (
        "No se graba. Queda en el registro de accesos que ve la familia en la app.",
        "privacidad",
        "health-live",
    )
    assert vivo.a_json()["health"]["ayuda"] == {
        "texto": "No se graba. Queda en el registro de accesos que ve la familia en la app.",
        "tema": "privacidad",
        "clave": "health-live",
    }
    assert estado(*TRES, zona=LIMA).aviso.ayuda is None


def test_pc_vinculada_sin_camaras_elegidas() -> None:
    from te_tengo_captura.estado import DatosPc, Entradas, derivar
    from tests.captura.estados import HOGAR

    e = derivar(
        Entradas((), True, True, 8, vinculada=True, webcams_detectadas=3),
        HOGAR,
        DatosPc("Sala-Rosa", "Windows 11 Home", "Te Tengo Captura 0.5.0"),
        "0.5.0",
    )
    assert e.aviso.titulo_html == "Falta elegir las cámaras en la app"
    assert e.aviso.detalle_html == (
        "Detectamos 3 cámaras. Mientras tanto, no cuida ninguna habitación."
    )
    assert e.aviso.accion is not None
    assert e.aviso.accion.act == "toCams"
    assert (e.bandeja.k, e.bandeja.etiqueta) == ("warn", "falta elegir las cámaras en la app")


def test_varias_camaras_perdidas_y_nombres_con_html() -> None:
    e = estado(
        camara("Sala <b>", webcam_conectada=False),
        camara("Pasillo", webcam_conectada=False),
        camara("Dormitorio"),
    )
    assert e.aviso.titulo_html == "Sala &lt;b&gt; y Pasillo no responden"
    assert e.aviso.detalle_html == "Revisa el cable USB · 1 de 3 cámaras funcionan"


def test_palabras_de_la_casa() -> None:
    assert de_habitacion("Sala") == "la sala"
    assert de_habitacion("dormitorio") == "el dormitorio"
    assert de_habitacion("Sala comedor") == "la habitación «Sala comedor»"
    assert del_habitacion("Dormitorio") == "del dormitorio"
    assert del_habitacion("Sala") == "de la sala"
    assert habitacion_arte("Pasillo") == "el Pasillo"
    assert habitacion_arte("Taller") == "«Taller»"
    assert lista_y(["Sala"]) == "Sala"
    assert lista_y(["Sala", "Dormitorio", "Pasillo"]) == "Sala, Dormitorio y Pasillo"
    assert hora_local(PAUSA, LIMA) == "11:42"


def test_json_para_la_interfaz() -> None:
    datos = estado(camara(pausada_hasta=PAUSA), zona=LIMA, en_linea=False).a_json()
    assert datos["screen"] == "main"
    assert datos["listo"] is True
    assert datos["situacion"] == "sin_internet"
    assert (datos["online"], datos["consent"], datos["retry"], datos["linked"]) == (
        False,
        True,
        8,
        False,
    )
    assert datos["home"] == {
        "who": "Rosa Huamán",
        "first": "Rosa",
        "addr": "Jr. Los Pinos 482, San Miguel, Lima",
    }
    assert datos["pc"]["nombre"] == PC.nombre
    assert datos["pc"]["instalada_el"] == "22/09/2026"
    assert datos["cams"][0]["room"] == "Sala"
    assert datos["cams"][0]["pause"] == "11:42"
    assert datos["devices"] == [
        {
            "id": "sala",
            "name": "Webcam USB HD",
            "uid": None,
            "room": "Sala",
            "connected": True,
            "busy": False,
            "new": False,
            "by": None,
            "preview": True,
            "peek": False,
            "skel": False,
        }
    ]
    assert datos["health"]["accion"] == {
        "act": "retryNow",
        "texto": "Reintentar ahora",
        "icono": "refresh",
    }
    assert datos["tray"] == {"k": "warn", "etiqueta": "sin internet, reintentando"}
    assert datos["version"] == "0.5.0"
    assert estado(en_linea=None).a_json()["listo"] is False


@pytest.mark.parametrize(
    ("camaras", "cambios", "texto"),
    [
        ((camara(),), {}, "Cuida la sala. Ábrelo junto al reloj."),
        (TRES, {}, "Cuida 3 habitaciones. Ábrelo junto al reloj."),
        (
            (camara(pausada_hasta=PAUSA),),
            {},
            "La sala en pausa hasta las 11:42.",
        ),
        (
            (camara(),),
            {"consentimiento": False},
            "Empieza cuando la familia registre el consentimiento.",
        ),
        (
            (camara(),),
            {"en_linea": False},
            "Sin internet: las cámaras siguen cuidando.",
        ),
        (
            (camara("Pasillo", webcam_conectada=False),),
            {},
            "La cámara del pasillo está desconectada: revisa el cable USB.",
        ),
    ],
)
def test_aviso_al_cerrar(camaras: tuple, cambios: dict[str, Any], texto: str) -> None:  # type: ignore[type-arg]
    aviso = aviso_al_cerrar(estado(*camaras, zona=LIMA, **cambios))
    assert aviso.titulo == "Sigue funcionando en segundo plano"
    assert aviso.texto == texto


def test_avisos_de_camara_y_de_vista_en_vivo() -> None:
    perdida = aviso_camara_desconectada("Pasillo")
    assert (perdida.titulo, perdida.texto) == (
        "La cámara del pasillo no responde",
        "Revisa el cable USB.",
    )
    vivo = aviso_en_vivo("Dormitorio")
    assert (vivo.titulo, vivo.texto) == (
        "Un familiar está viendo el dormitorio en vivo",
        "No se graba · queda registrado.",
    )


def test_estado_inmutable() -> None:
    e = estado()
    with pytest.raises(AttributeError):
        e.situacion = Situacion.EN_PAUSA  # type: ignore[misc]


def test_bandeja_violeta_cuando_miran_una_camara_para_elegirla() -> None:
    from dataclasses import replace as cambiar

    from tests.captura.estados import entradas, webcam_de

    e = entradas(camara())
    mirada = cambiar(webcam_de(camara()), mirando=True)
    from te_tengo_captura.estado import derivar
    from tests.captura.estados import HOGAR

    estado_ = derivar(cambiar(e, webcams=(mirada,)), HOGAR, PC, "0.5.0")
    assert (estado_.bandeja.k, estado_.bandeja.etiqueta) == (
        "live",
        "Un familiar mira una cámara para elegirla",
    )
    assert estado_.a_json()["devices"][0]["peek"] is True
