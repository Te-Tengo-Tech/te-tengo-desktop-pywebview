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
            ("ok", "send", "check", "Te Tengo está cuidando la sala", "Todo funciona bien.", None),
            ("send", "En línea", "Todo funciona bien", "check"),
            ("ok", "cuidando la sala"),
        ),
        (
            TRES,
            {},
            (
                "ok",
                "send",
                "check",
                "Te Tengo está cuidando 3 habitaciones",
                "Sala, Dormitorio y Pasillo · Todo funciona bien.",
                None,
            ),
            ("send", "En línea", "Todo funciona bien", "check"),
            ("ok", "cuidando 3 habitaciones"),
        ),
        (
            (camara(), camara("Dormitorio"), camara("Pasillo", webcam_conectada=False)),
            {},
            (
                "warn lost",
                "off",
                "videoOff",
                "2 de 3 cámaras funcionan · Pasillo no responde",
                "Revisa el cable USB de la USB2.0 PC Camera. Las demás cámaras siguen cuidando.",
                ("rescan", "Buscar de nuevo", "refresh"),
            ),
            ("send", "En línea", "Todo funciona bien", "check"),
            ("warn", "una cámara no responde"),
        ),
        (
            (camara(webcam_conectada=False),),
            {},
            (
                "warn lost",
                "off",
                "videoOff",
                "La cámara de la sala no responde",
                "Revisa que el cable USB esté bien conectado a la PC.",
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
                'Las cámaras siguen cuidando y los avisos esperan. Volvemos a intentar en <span class="mono" id="retry">8</span> s.',
                ("retryNow", "Reintentar ahora", "refresh"),
            ),
            ("warn", "Sin internet", "Detecta igual; los avisos esperan", "wifiOff"),
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
                "La familia debe registrarlo en la app Te Tengo. Mientras tanto, las cámaras no se usan.",
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
                "Dormitorio y Pasillo siguen cuidando. La familia la pausó desde la app Te Tengo; vuelve sola a esa hora.",
                None,
            ),
            (
                "pause",
                "En pausa",
                'Hasta las <span class="mono">11:42</span> · desde la app',
                "pause",
            ),
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
                'Desde las <span class="mono">10:42</span>. No se graba y queda en el registro de la familia.',
                None,
            ),
            ("live", "En vivo", "Un familiar está mirando", "eye"),
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
        "Detectamos 3 cámaras. Elígelas desde la app Te Tengo, en tu celular. "
        "Mientras tanto, esta PC no cuida ninguna habitación."
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
    assert e.aviso.titulo_html == (
        "1 de 3 cámaras funcionan · Sala &lt;b&gt; y Pasillo no responden"
    )
    assert e.aviso.detalle_html == (
        "Revisa que el cable USB esté bien conectado a la PC. Las demás cámaras siguen cuidando."
    )


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
        ((camara(),), {}, "Sigue cuidando la sala. Ábrelo desde su ícono, junto al reloj."),
        (TRES, {}, "Sigue cuidando 3 habitaciones. Ábrelo desde su ícono, junto al reloj."),
        (
            (camara(pausada_hasta=PAUSA),),
            {},
            "La sala está en pausa hasta las 11:42. Ábrelo desde su ícono, junto al reloj.",
        ),
        (
            (camara(),),
            {"consentimiento": False},
            "Empezará cuando la familia registre el consentimiento en la app Te Tengo.",
        ),
        (
            (camara(),),
            {"en_linea": False},
            "Las cámaras siguen cuidando y seguirá intentando conectarse a internet. Ábrelo desde su ícono, junto al reloj.",
        ),
        (
            (camara("Pasillo", webcam_conectada=False),),
            {},
            "La cámara del pasillo está desconectada: revisa el cable USB. Ábrelo desde su ícono, junto al reloj.",
        ),
    ],
)
def test_aviso_al_cerrar(camaras: tuple, cambios: dict[str, Any], texto: str) -> None:  # type: ignore[type-arg]
    aviso = aviso_al_cerrar(estado(*camaras, zona=LIMA, **cambios))
    assert aviso.titulo == "Te Tengo Captura sigue funcionando en segundo plano"
    assert aviso.texto == texto


def test_avisos_de_camara_y_de_vista_en_vivo() -> None:
    perdida = aviso_camara_desconectada("Pasillo")
    assert (perdida.titulo, perdida.texto) == (
        "La cámara del pasillo no responde",
        "Revisa que el cable USB esté bien conectado a la PC.",
    )
    vivo = aviso_en_vivo("Dormitorio")
    assert (vivo.titulo, vivo.texto) == (
        "Un familiar está viendo el dormitorio en vivo",
        "No se graba y queda en el registro de la familia.",
    )


def test_estado_inmutable() -> None:
    e = estado()
    with pytest.raises(AttributeError):
        e.situacion = Situacion.EN_PAUSA  # type: ignore[misc]
