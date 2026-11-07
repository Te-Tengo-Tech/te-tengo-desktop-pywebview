"""The window's texts (``ui/web/textos.js``): the Spanish and English catalogs are complete.

``textos.js`` holds strict JSON after ``TTG_TEXTOS =``; ``app.js`` reads it with ``tx(id, {name})``
(``tn`` for one/several). Both languages have the same ids and the same ``{placeholders}``, every
id ``app.js`` asks for exists, and every id is used.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from te_tengo_captura.ui.ventana import WEB

PRUEBA_JS = Path(__file__).with_name("app_en.test.js")
MARCA = "TTG_TEXTOS = "
# formats whose pieces differ by language («23/09/2026», «Sep 23, 2026»): only known pieces
FORMATOS = {"fmt.fecha": {"d", "dd", "m", "mes", "y"}}
# ids built at run time in app.js: plurals (tn), the month names and the arrays of ids
DINAMICAS = re.compile(
    r"^(fmt\.mes\.\d+|met\.punto\.\w+|log\.(personas|eventos|descartadas|conexion|programa)"
    r"|fase\.\w+|rp\.(inestable|confirmada|levanto|q15|q60|q7)|diag\.[in]\d|idioma\.(es|en))$"
)


def _catalogo() -> dict[str, dict[str, str]]:
    texto = (WEB / "textos.js").read_text(encoding="utf-8")
    inicio = texto.index(MARCA) + len(MARCA)
    fin = texto.rindex(";")
    datos: dict[str, dict[str, str]] = json.loads(texto[inicio:fin])
    return datos


def _marcadores(texto: str) -> set[str]:
    return set(re.findall(r"\{(\w+)\}", texto))


def test_mismos_ids_en_espanol_e_ingles() -> None:
    catalogo = _catalogo()
    assert set(catalogo) == {"es", "en"}
    assert set(catalogo["es"]) == set(catalogo["en"])
    assert all(isinstance(v, str) and v for idioma in catalogo.values() for v in idioma.values())


def test_mismos_marcadores_en_cada_texto() -> None:
    catalogo = _catalogo()
    distintos = {
        clave: (texto, catalogo["en"][clave])
        for clave, texto in catalogo["es"].items()
        if clave not in FORMATOS and _marcadores(texto) != _marcadores(catalogo["en"][clave])
    }
    assert distintos == {}
    for clave, piezas in FORMATOS.items():
        assert _marcadores(catalogo["es"][clave]) | _marcadores(catalogo["en"][clave]) <= piezas


def test_los_plurales_tienen_sus_dos_formas() -> None:
    claves = set(_catalogo()["es"])
    for clave in claves:
        if clave.endswith(".uno"):
            assert clave.removesuffix(".uno") + ".otros" in claves


def test_app_js_solo_pide_ids_que_existen_y_todos_se_usan() -> None:
    claves = set(_catalogo()["es"])
    js = (WEB / "app.js").read_text(encoding="utf-8")
    pedidas = set(re.findall(r"\btx\('([\w.]+)'(?!\s*\+)", js))
    plurales = {
        f"{base}.{forma}"
        for base in re.findall(r"\btn\('([\w.]+)'", js)
        for forma in ("uno", "otros")
    }
    assert pedidas - claves == set()
    assert plurales - claves == set()
    sin_usar = {c for c in claves - pedidas - plurales if not DINAMICAS.match(c)}
    assert sin_usar == set()


def test_los_textos_no_cierran_un_atributo_html() -> None:
    """Texts go inside ``aria-label="…"`` and ``title="…"``: no double quotes."""
    for idioma in _catalogo().values():
        assert [c for c, v in idioma.items() if '"' in v] == []


def test_las_paginas_cargan_los_textos_antes_que_app_js() -> None:
    for pagina in ("index.html", "arranque.html"):
        html = (WEB / pagina).read_text(encoding="utf-8")
        assert html.index('src="textos.js"') < html.index('src="app.js"')


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js no está instalado")
def test_la_ventana_en_ingles_en_node() -> None:
    from tests.captura.estados import camara, estado
    from tests.captura.ui.test_puente import _pantallas_de_vinculacion

    tres = (camara("Sala"), camara("Dormitorio"), camara("Pasillo"))
    estados: dict[str, Any] = {
        "uno": estado(camara()).a_json(),
        "tres": estado(*tres).a_json(),
        "vincular": _pantallas_de_vinculacion()["vincular"],
    }
    resultado = subprocess.run(
        ["node", str(PRUEBA_JS), str(WEB / "app.js")],
        input=json.dumps(estados),
        capture_output=True,
        text=True,
        check=False,
    )
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
