"""The window rendered in Chromium matches the prototype screens (docs/references/desktop-prototype).

Runs where Node.js, Playwright and Chromium are available (the cloud environment has them; locally
set ``TT_PLAYWRIGHT`` to a ``node_modules/playwright`` folder and ``TT_CHROMIUM`` to a Chromium
binary); skipped elsewhere. The prototype draws a PC with three cameras and names who did each
thing («Luis la pausó», «Carmen está viendo»); the agent does not know those names, so only the
screens whose copy the agent reproduces exactly are compared, and only below the tab bar (the
prototype also shows the «Avanzado» tab) and above the prototype's bottom band. Differences come only from anti-aliasing.
"""

import json
import os
import shutil
import subprocess
from datetime import timedelta, timezone
from pathlib import Path

import pytest
from PIL import Image, ImageChops

from te_tengo_captura.ui.ventana import WEB
from tests.captura.estados import camara, estado

PANTALLAS = Path(__file__).resolve().parents[3] / "docs/references/desktop-prototype/screens"
CHROMIUM = Path(os.environ.get("TT_CHROMIUM", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"))
LIMA = timezone(timedelta(hours=-5))
TOLERANCIA = 0.005  # share of pixels that may differ (anti-aliasing)
DEBAJO_DE_LAS_PESTANAS = 2 * (36 + 50)  # title bar and tab bar, at 2x
# The prototype's bottom band («Se inicia con Windows») is not drawn by the real window (it looked
# like the simulated taskbar); the comparison stops above it.
BANDA_INFERIOR = 2 * 52


def _playwright() -> Path | None:
    if propio := os.environ.get("TT_PLAYWRIGHT"):
        return Path(propio)
    if shutil.which("npm") is None:
        return None
    raiz = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True, check=False)
    ruta = Path(raiz.stdout.strip()) / "playwright"
    return ruta if ruta.is_dir() else None


PLAYWRIGHT = _playwright()

pytestmark = pytest.mark.skipif(
    PLAYWRIGHT is None or not CHROMIUM.is_file() or shutil.which("node") is None,
    reason="Necesita Node.js, Playwright y Chromium",
)

TRES = (camara("Sala"), camara("Dormitorio"), camara("Pasillo"))
VARIANTES = {
    "01-enviando-video": estado(*TRES, zona=LIMA),
    "03-esperando-consentimiento": estado(*TRES, zona=LIMA, consentimiento=False),
    "04-sin-internet": estado(*TRES, zona=LIMA, en_linea=False),
    "05-webcam-desconectada": estado(
        camara("Sala"), camara("Dormitorio"), camara("Pasillo", webcam_conectada=False), zona=LIMA
    ),
}


def test_la_ventana_coincide_con_las_pantallas_del_prototipo(tmp_path: Path) -> None:
    estados = {nombre: e.a_json() for nombre, e in VARIANTES.items()}
    resultado = subprocess.run(
        [
            "node",
            str(Path(__file__).with_name("pantallas.js")),
            str(PLAYWRIGHT),
            str(CHROMIUM),
            str(WEB / "index.html"),
            str(tmp_path),
        ],
        input=json.dumps(estados),
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert resultado.returncode == 0, resultado.stderr
    for nombre in VARIANTES:
        esperada = Image.open(PANTALLAS / f"{nombre}.png").convert("L")
        obtenida = Image.open(tmp_path / f"{nombre}.png").convert("L")
        assert obtenida.size == esperada.size
        caja = (0, DEBAJO_DE_LAS_PESTANAS, esperada.size[0], esperada.size[1] - BANDA_INFERIOR)
        diferencia = ImageChops.difference(esperada.crop(caja), obtenida.crop(caja)).point(
            lambda v: 255 if v > 40 else 0
        )
        distintos = diferencia.histogram()[255] / ((caja[2] - caja[0]) * (caja[3] - caja[1]))
        assert distintos < TOLERANCIA, f"{nombre}: {distintos:.2%} de píxeles distintos"


def test_la_cuenta_regresiva_no_mueve_el_foco() -> None:
    sin_internet = estado(camara(), en_linea=False)
    resultado = subprocess.run(
        [
            "node",
            str(Path(__file__).with_name("foco.js")),
            str(PLAYWRIGHT),
            str(CHROMIUM),
            str(WEB / "index.html"),
        ],
        input=json.dumps(sin_internet.a_json()),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert resultado.returncode == 0, resultado.stderr


def test_el_arranque_coincide_con_la_pantalla_00(tmp_path: Path) -> None:
    salida = tmp_path / "00.png"
    resultado = subprocess.run(
        [
            "node",
            str(Path(__file__).with_name("arranque.js")),
            str(PLAYWRIGHT),
            str(CHROMIUM),
            str(WEB / "arranque.html"),
            str(salida),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert resultado.returncode == 0, resultado.stderr
    # In the prototype PNG the 480 × 300 window sits on a desktop; compare that region.
    esperada = (
        Image.open(PANTALLAS / "00-pantalla-de-arranque.png")
        .convert("L")
        .crop((480, 296, 1440, 896))
    )
    obtenida = Image.open(salida).convert("L")
    assert obtenida.size == esperada.size
    # Ignore the 10 px rounded corners of the mock-up frame.
    margen = 24
    caja = (margen, margen, esperada.size[0] - margen, esperada.size[1] - margen)
    diferencia = ImageChops.difference(esperada.crop(caja), obtenida.crop(caja)).point(
        lambda v: 255 if v > 40 else 0
    )
    distintos = diferencia.histogram()[255] / ((caja[2] - caja[0]) * (caja[3] - caja[1]))
    assert distintos < TOLERANCIA, f"{distintos:.2%} de píxeles distintos"
