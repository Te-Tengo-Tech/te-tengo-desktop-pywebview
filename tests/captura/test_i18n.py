"""Language of the window, the tray and the notices: Spanish by default, English on request."""

import json
import logging
import re
from collections.abc import Iterator
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest

from te_tengo_captura import config, i18n
from te_tengo_captura.actividad import RegistroActividad, para_la_ventana
from te_tengo_captura.almacen.gestor import AjustesAlmacen, _cambios, texto_dias
from te_tengo_captura.bandeja.icono import texto_abrir, texto_buscar, texto_descarga, texto_salir
from te_tengo_captura.coordinador import ARCHIVO_VENTANA, Coordinador, idioma_elegido
from te_tengo_captura.diario import Diario, ManejadorDiario, anotar
from te_tengo_captura.estado import (
    aviso_al_cerrar,
    aviso_camara_desconectada,
    aviso_en_vivo,
    aviso_pc_quitada,
    aviso_version_nueva,
    de_habitacion,
    lista_y,
)
from tests.captura.estados import camara, estado

SRC = Path(__file__).resolve().parents[2] / "src/te_tengo_captura"
PALABRAS_EN_ESPANOL = re.compile(
    r"\b(cámaras?|cuida|habitaci[oó]n(es)?|internet,|pausa|vivo|revisa|falta|familia|"
    r"sigue|funciona|bien|línea|desconectada|consentimiento|reintento|desde|hasta)\b",
    re.IGNORECASE,
)


@pytest.fixture
def ingles() -> Iterator[None]:
    i18n.establecer(i18n.EN)
    yield
    i18n.establecer(i18n.ES)


def _marcadores(texto: str) -> set[str]:
    return set(re.findall(r"\{(\w+)\}", texto))


# ------------------------------------------------------------------ the catalogs


def test_espanol_e_ingles_tienen_los_mismos_ids() -> None:
    es, en = i18n.CATALOGOS[i18n.ES], i18n.CATALOGOS[i18n.EN]
    assert set(es) - set(en) == set()
    assert set(en) - set(es) == set()


def test_cada_texto_tiene_los_mismos_marcadores_en_los_dos_idiomas() -> None:
    es, en = i18n.CATALOGOS[i18n.ES], i18n.CATALOGOS[i18n.EN]
    distintos = {c: (es[c], en[c]) for c in es if _marcadores(es[c]) != _marcadores(en[c])}
    assert distintos == {}


def test_ningun_texto_queda_vacio() -> None:
    for idioma, catalogo in i18n.CATALOGOS.items():
        assert [c for c, texto in catalogo.items() if not texto.strip()] == [], idioma


def test_los_plurales_tienen_sus_dos_formas() -> None:
    claves = set(i18n.CATALOGOS[i18n.ES])
    for clave in claves:
        if clave.endswith((".uno", ".otros")):
            base = clave.rsplit(".", 1)[0]
            assert {f"{base}.uno", f"{base}.otros"} <= claves, base


def test_el_codigo_solo_pide_ids_que_existen() -> None:
    """Every literal id in ``t("…")``, ``frase("…")`` and ``traducir(…, "…")`` is in the catalog."""
    claves = set(i18n.CATALOGOS[i18n.ES])
    patron = re.compile(r"""\b(?:t|frase|traducir\([^,()]+,)\(?\s*"([a-z_]+(?:\.[\w]+)+)\"""")
    pedidas: set[str] = set()
    for ruta in SRC.rglob("*.py"):
        pedidas |= set(patron.findall(ruta.read_text(encoding="utf-8")))
    assert len(pedidas) > 50  # the pattern finds them
    dinamicas = {c for c in pedidas if c.endswith(".")}
    assert pedidas - dinamicas - claves == set()


def test_un_id_que_falta_cae_al_espanol_y_luego_al_id() -> None:
    assert i18n.traducir("fr", "camara.en_linea") == "En línea"
    assert i18n.traducir(i18n.EN, "no.existe") == "no.existe"


# ------------------------------------------------------------------ choosing the language


@pytest.mark.parametrize(
    ("codigo", "idioma"),
    [
        ("en_US.UTF-8", "en"),
        ("en-GB", "en"),
        ("EN", "en"),
        ("es_PE.UTF-8", "es"),
        ("es-419", "es"),
        ("pt_BR", "es"),
        ("fr", "es"),
        ("", "es"),
        (None, "es"),
    ],
)
def test_el_idioma_del_sistema_es_ingles_solo_si_empieza_con_en(
    codigo: str | None, idioma: str
) -> None:
    assert i18n.de_la_configuracion_regional(codigo) == idioma
    assert i18n.elegir(sistema=lambda: codigo) == idioma


def test_la_eleccion_de_la_ventana_gana_a_la_configuracion_y_esta_al_sistema() -> None:
    sistema_en = lambda: "en_US"  # noqa: E731
    assert i18n.elegir(None, None, sistema_en) == "en"
    assert i18n.elegir(None, "es", sistema_en) == "es"
    assert i18n.elegir("en", "es", lambda: "es_PE") == "en"
    assert i18n.elegir("de", None, lambda: "es_PE") == "es"  # unsupported: ignored


def test_idioma_del_sistema_por_las_variables_de_entorno() -> None:
    assert i18n.idioma_del_sistema({"LANG": "en_US.UTF-8"}, "linux") == "en_US.UTF-8"
    assert i18n.idioma_del_sistema({"LC_ALL": "es_PE.UTF-8", "LANG": "en_US"}, "linux") == (
        "es_PE.UTF-8"
    )
    assert i18n.idioma_del_sistema({"LANGUAGE": "en_GB:en"}, "linux") == "en_GB"
    # «C» says nothing about the language: the next source is asked.
    assert i18n.idioma_del_sistema({"LANG": "C", "LANGUAGE": "en"}, "linux") == "en"


def test_establecer_un_idioma_no_soportado_vuelve_al_espanol() -> None:
    assert i18n.establecer("en-US") == "en"
    assert i18n.establecer("qu") == "es"
    assert i18n.idioma() == "es"


def test_interfaz_idioma_en_el_archivo_de_configuracion(tmp_path: Path) -> None:
    ruta = tmp_path / "config.toml"
    ruta.write_text('[interfaz]\nidioma = "en"\n', encoding="utf-8")
    ajustes = config.cargar(ruta)
    assert ajustes.interfaz.idioma == "en"
    assert config.AjustesPc().interfaz.idioma is None  # by default: the system's
    ruta.write_text('[interfaz]\nidioma = "fr"\n', encoding="utf-8")
    with pytest.raises(config.ConfiguracionInvalidaError, match=r"interfaz\.idioma"):
        config.cargar(ruta)


def test_la_instalacion_de_ejemplo_no_fija_el_idioma(configuracion: config.Configuracion) -> None:
    assert configuracion.interfaz.idioma is None


def test_el_idioma_elegido_en_la_ventana_se_recuerda(tmp_path: Path) -> None:
    from te_tengo_captura.backend.falso import URL_API
    from te_tengo_captura.vinculacion.credenciales import AlmacenCredenciales, LlaveroEnMemoria

    assert idioma_elegido(tmp_path) is None
    coordinador = Coordinador(
        "1.0.0",
        URL_API,
        tmp_path,
        AlmacenCredenciales(LlaveroEnMemoria()),
        canal_pc=False,
        plataforma=None,
    )
    publicados: list[dict[str, Any]] = []
    coordinador.suscribir(lambda e: publicados.append(e.a_json()))
    assert coordinador.cambiar_idioma("en") == "en"
    assert i18n.idioma() == "en"
    assert publicados[-1]["idioma"] == "en"  # the window gets it at once
    assert publicados[-1]["screen"] == "vincular"
    assert coordinador.estado().bandeja.etiqueta == "not linked"
    assert idioma_elegido(tmp_path) == "en"
    assert json.loads((tmp_path / ARCHIVO_VENTANA).read_text("utf-8"))["idioma"] == "en"
    assert coordinador.cambiar_idioma("xx") == "en"  # unsupported: nothing changes


def test_main_elige_el_idioma_antes_de_construir(tmp_path: Path) -> None:
    from te_tengo_captura.__main__ import argumentos, elegir_idioma

    args = argumentos(["--datos", str(tmp_path)])
    ajustes = config.AjustesPc(interfaz=config.Interfaz(idioma="en"))
    assert elegir_idioma(args, ajustes) == "en"
    (tmp_path / ARCHIVO_VENTANA).write_text('{"idioma": "es"}', encoding="utf-8")
    assert elegir_idioma(args, ajustes) == "es"  # the window's choice wins
    assert i18n.idioma() == "es"


# ------------------------------------------------------------------ what people read


def test_el_estado_en_espanol_no_cambia() -> None:
    datos = estado(camara("Sala")).a_json()
    assert datos["idioma"] == "es"
    assert datos["health"]["titulo_html"] == "Te Tengo cuida la sala"
    assert datos["health"]["detalle_html"] == "Todo funciona bien."
    assert datos["cams"][0]["st"]["titulo"] == "En línea"
    assert datos["tray"]["etiqueta"] == "cuidando la sala"
    assert datos["pc"]["instalada_el"] == "22/09/2026"


@pytest.mark.usefixtures("ingles")
def test_el_estado_en_ingles() -> None:
    datos = estado(camara("Sala")).a_json()
    assert datos["idioma"] == "en"
    assert datos["health"]["titulo_html"] == "Te Tengo is looking after Sala"
    assert datos["health"]["detalle_html"] == "Everything is working well."
    assert datos["cams"][0]["st"]["titulo"] == "Online"
    assert datos["tray"]["etiqueta"] == "looking after Sala"
    # Household data stays as the family wrote it.
    assert datos["home"] == {
        "who": "Rosa Huamán",
        "first": "Rosa",
        "addr": "Jr. Los Pinos 482, San Miguel, Lima",
    }
    assert datos["cams"][0]["room"] == "Sala"


@pytest.mark.usefixtures("ingles")
@pytest.mark.parametrize(
    "cambios",
    [
        {},
        {"en_linea": False},
        {"consentimiento": False},
        {"vinculada": True, "camaras": (), "webcams_detectadas": 0},
        {"vinculada": True, "camaras": (), "webcams_detectadas": 2},
    ],
)
def test_ningun_resumen_queda_en_espanol(cambios: dict[str, Any]) -> None:
    datos = estado(camara("Sala"), camara("Dormitorio"), **cambios).a_json()
    textos = [
        datos["health"]["titulo_html"],
        datos["health"]["detalle_html"],
        datos["tray"]["etiqueta"],
        *(c["st"]["titulo"] for c in datos["cams"]),
        *(c["st"]["detalle_html"] for c in datos["cams"]),
    ]
    if datos["health"]["accion"]:
        textos.append(datos["health"]["accion"]["texto"])
    sala_y_dormitorio = re.compile(r"\b(Sala|Dormitorio)\b")
    for texto in textos:
        assert not PALABRAS_EN_ESPANOL.search(sala_y_dormitorio.sub("", texto)), texto


@pytest.mark.usefixtures("ingles")
def test_resumenes_en_ingles_con_pausa_vivo_y_camaras_perdidas() -> None:
    hora = datetime(2026, 9, 23, 20, 0, tzinfo=UTC)
    pausa = estado(camara("Sala", pausada_hasta=hora), camara("Dormitorio"), zona=UTC)
    assert pausa.aviso.titulo_html == 'Sala is paused until <span class="mono">20:00</span>'
    assert (
        pausa.aviso.detalle_html == "Dormitorio is still watching · paused by the family in the app"
    )
    vivo = estado(camara("Sala", en_vivo_desde=hora), zona=UTC)
    assert vivo.aviso.titulo_html == "A family member is watching Sala live"
    assert vivo.aviso.ayuda is not None
    assert vivo.aviso.ayuda.tema == "privacy"
    perdidas = estado(
        camara("Sala", webcam_conectada=False),
        camara("Dormitorio", webcam_conectada=False),
        camara("Pasillo"),
    )
    assert perdidas.aviso.titulo_html == "Sala and Dormitorio aren&#x27;t responding"
    assert perdidas.aviso.detalle_html == "Check the USB cable · 1 of 3 cameras working"
    assert lista_y(["Sala", "Dormitorio", "Pasillo"]) == "Sala, Dormitorio and Pasillo"
    assert de_habitacion("Sala") == "Sala"


@pytest.mark.usefixtures("ingles")
def test_notificaciones_en_ingles() -> None:
    cerrada = aviso_al_cerrar(estado(camara("Sala")))
    assert (cerrada.titulo, cerrada.texto) == (
        "Still running in the background",
        "Looking after Sala. Open it next to the clock.",
    )
    assert aviso_camara_desconectada("Sala").titulo == "The Sala camera isn't responding"
    assert aviso_en_vivo("Sala").texto == "It isn't recorded · it's logged."
    assert aviso_version_nueva("0.8.0").titulo == "A new version is available: 0.8.0"
    assert aviso_pc_quitada("10:42").texto == (
        "The family removed it at 10:42. Open it to link it again."
    )


def test_el_menu_de_la_bandeja_sigue_el_idioma() -> None:
    assert [texto_abrir(), texto_buscar(), texto_salir()] == [
        "Abrir Te Tengo Captura",
        "Buscar actualizaciones",
        "Salir",
    ]
    assert texto_descarga("0.8.0", mac=True) == "Ir a la descarga de la versión 0.8.0"
    i18n.establecer(i18n.EN)
    assert [texto_abrir(), texto_buscar(), texto_salir()] == [
        "Open Te Tengo Captura",
        "Check for updates",
        "Quit",
    ]
    assert texto_descarga("0.8.0", mac=False) == "Download version 0.8.0"


def test_fechas_y_decimales_por_idioma() -> None:
    dia = date(2026, 9, 3)
    assert (i18n.fecha(dia), i18n.fecha_corta(dia), i18n.decimal(1.48, 2)) == (
        "03/09/2026",
        "03/09",
        "1,48",
    )
    assert (i18n.fecha(dia, "en"), i18n.fecha_corta(dia, "en"), i18n.decimal(1.48, 2, "en")) == (
        "Sep 3, 2026",
        "Sep 3",
        "1.48",
    )


# ------------------------------------------------------------------ what is never translated


def test_la_actividad_guarda_el_espanol_y_muestra_el_idioma_de_la_ventana(tmp_path: Path) -> None:
    ahora = datetime(2026, 9, 23, 15, 42, tzinfo=UTC)
    registro = RegistroActividad(tmp_path, reloj_utc=lambda: ahora)
    registro.anotar(
        i18n.frase("actividad.avanzado.on"), tipo="MODO_AVANZADO_ACTIVADO", objeto="Avanzado"
    )
    entrada = json.loads((tmp_path / "actividad.jsonl").read_text("utf-8"))
    assert entrada["texto"] == "Desde esta PC: se activó el modo avanzado"
    assert entrada["texto_en"] == "From this PC: advanced mode turned on"
    enviados: list[list[dict[str, Any]]] = []

    class Remitente:
        def actividad(self, cambios: list[dict[str, Any]]) -> None:
            enviados.append(cambios)

    registro.enviar(Remitente())
    # The API gets exactly what it got before: no text, the Spanish object.
    assert enviados[0][0].keys() == {"id", "tipo", "ocurridoEn", "objeto"}
    assert enviados[0][0]["objeto"] == "Avanzado"
    assert para_la_ventana(registro.entradas(), UTC, ahora)[0]["m"].startswith("Desde esta PC")
    i18n.establecer(i18n.EN)
    fila = para_la_ventana(registro.entradas(), UTC, ahora)[0]
    assert (fila["d"], fila["m"]) == ("Today", "From this PC: advanced mode turned on")


def test_los_cambios_de_almacenamiento_mandan_valores_en_espanol() -> None:
    i18n.establecer(i18n.EN)
    (cambio,) = _cambios(AjustesAlmacen(), AjustesAlmacen(dias_movimientos=30))
    assert (cambio.objeto, cambio.anterior, cambio.nuevo) == ("Movimientos", "90 días", "30 días")
    assert cambio.texto == "Desde esta PC: los movimientos pasaron de 90 días a 30 días"
    assert cambio.frase is not None
    assert cambio.frase("en") == "From this PC: movements changed from 90 days to 30 days"
    assert texto_dias(None, "en") == "Never delete"


def test_el_registro_del_programa_sigue_en_espanol_y_la_ventana_en_ingles(
    caplog: pytest.LogCaptureFixture,
) -> None:
    diario = Diario()
    diario.activo = True
    manejador = ManejadorDiario(diario)
    logging.getLogger().addHandler(manejador)
    try:
        i18n.establecer(i18n.EN)
        with caplog.at_level(logging.INFO, logger="te_tengo_captura.diario"):
            anotar("c1", "evento", "calma", "arrowUp", i18n.frase("diario.se_levanto"), "INFO x")
    finally:
        logging.getLogger().removeHandler(manejador)
    assert [r.getMessage() for r in caplog.records] == ["Se levantó"]
    assert [linea.texto for linea in diario.desde("c1")] == ["Got up"]
