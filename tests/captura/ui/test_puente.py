import json
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest

from te_tengo_captura.ui.puente import Puente
from te_tengo_captura.ui.ventana import WEB, script_actualizar

PRUEBA_JS = Path(__file__).with_name("app.test.js")


class Llamadas:
    def __init__(self) -> None:
        self.ocultar = 0

    def ocultado(self) -> None:
        self.ocultar += 1


def test_el_puente_expone_solo_los_metodos_del_contrato() -> None:
    llamadas = Llamadas()
    puente = Puente(
        lambda: {"situacion": "cuidando"},
        llamadas.ocultado,
        lambda: False,
        lambda: True,
        lambda clave: b"\xff\xd8jpeg" if clave == "sala" else None,
    )
    publicos = {n for n in dir(puente) if not n.startswith("_")}
    assert publicos == {
        "estado",
        "minimizar",
        "cerrar",
        "buscarWebcam",
        "reintentarAhora",
        "vistaPrevia",
    }
    assert puente.estado() == {"situacion": "cuidando"}
    assert puente.vistaPrevia("sala") == {"jpeg": "/9hqcGVn"}
    assert puente.vistaPrevia("otra") == {"jpeg": None}
    puente.minimizar()
    puente.cerrar()
    assert llamadas.ocultar == 2  # both hide to the tray, neither stops the agent
    assert puente.buscarWebcam() == {"ok": False}
    assert puente.reintentarAhora() == {"ok": True}


def test_script_de_actualizacion_es_ascii_y_json() -> None:
    script = script_actualizar({"room": "Habitación </script>", "retry": 8})
    assert script.isascii()
    datos = json.loads(
        script.removeprefix("window.ttg && window.ttg.actualizar(").removesuffix(")")
    )
    assert datos == {"room": "Habitación </script>", "retry": 8}


class _Recursos(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.urls += [v for k, v in attrs if k in ("src", "href") and v]


@pytest.mark.parametrize("pagina", sorted(p.name for p in WEB.glob("*.html")))
def test_el_html_solo_usa_recursos_locales(pagina: str) -> None:
    parser = _Recursos()
    parser.feed((WEB / pagina).read_text(encoding="utf-8"))
    assert parser.urls
    for url in parser.urls:
        assert not re.match(r"^([a-z]+:)?//", url), url
        assert (WEB / url).is_file(), url
    css = (WEB / "app.css").read_text(encoding="utf-8")
    for url in re.findall(r"url\(\"?([^\")]+)\"?\)", css):
        if url.startswith("data:"):
            continue  # inline images (the select's chevron): nothing is fetched
        assert not re.match(r"^([a-z]+:)?//", url), url
        assert (WEB / url).is_file(), url
    js = (WEB / "app.js").read_text(encoding="utf-8")
    assert "http://" not in js
    assert "https://" not in js


def test_fuentes_con_su_licencia() -> None:
    assert (WEB / "fonts" / "OFL.txt").is_file()


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js no está instalado")
def test_render_de_la_ventana_en_node() -> None:
    from datetime import UTC, datetime

    from tests.captura.estados import camara, estado

    pausa = datetime(2026, 10, 7, 20, 0, tzinfo=UTC)
    tres = (camara("Sala"), camara("Dormitorio"), camara("Pasillo"))
    variantes = {
        "uno": estado(camara()),
        "tres": estado(*tres),
        "pausa": estado(camara(pausada_hasta=pausa), camara("Dormitorio")),
        "consentimiento": estado(camara(), consentimiento=False),
        "internet": estado(camara(), en_linea=False),
        "perdida": estado(camara(webcam_conectada=False), camara("Dormitorio")),
        "vivo": estado(camara(en_vivo_desde=pausa)),
        "html": estado(camara("Dormitorio <b>")),
        "renombrada": estado(camara(nombre_habitacion="Sala comedor")),
    }
    estados = {nombre: e.a_json() for nombre, e in variantes.items()}
    resultado = subprocess.run(
        ["node", str(PRUEBA_JS), str(WEB / "app.js")],
        input=json.dumps(estados),
        capture_output=True,
        text=True,
        check=False,
    )
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
