"""The window rendered in Chromium matches the prototype screens 01–05.

Runs where Node.js, Playwright and Chromium are available (the cloud environment has them);
skipped elsewhere. Differences come only from anti-aliasing, so the tolerance is small.
"""

import json
import shutil
import subprocess
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from PIL import Image, ImageChops

from te_tengo_captura.config import Configuracion
from te_tengo_captura.estado import Entradas, derivar
from te_tengo_captura.ui.ventana import WEB

PANTALLAS = Path(__file__).resolve().parents[3] / "docs/references/desktop-prototype/screens"
CHROMIUM = Path("/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
LIMA = timezone(timedelta(hours=-5))
TOLERANCIA = 0.005  # share of pixels that may differ (anti-aliasing)


def _playwright() -> Path | None:
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

VARIANTES: dict[str, dict[str, Any]] = {
    "01-enviando-video": {},
    "02-en-pausa": {"pausada_hasta": datetime(2026, 10, 7, 20, 0, tzinfo=UTC)},
    "03-esperando-consentimiento": {"consentimiento": False},
    "04-sin-internet": {"en_linea": False},
    "05-webcam-desconectada": {"webcam_conectada": False},
}


def test_la_ventana_coincide_con_las_pantallas_del_prototipo(
    tmp_path: Path, configuracion: Configuracion
) -> None:
    base: dict[str, Any] = {
        "webcam_conectada": True,
        "en_linea": True,
        "consentimiento": True,
        "pausada_hasta": None,
        "segundos_desde_envio": 2,
        "segundos_para_reintento": 8,
        "nombre_habitacion": "Sala",
    }
    estados = {
        nombre: derivar(Entradas(**{**base, **cambios}), configuracion, "1.0.0", LIMA).a_json()
        for nombre, cambios in VARIANTES.items()
    }
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
        diferencia = ImageChops.difference(esperada, obtenida).point(lambda v: 255 if v > 40 else 0)
        distintos = diferencia.histogram()[255] / (esperada.size[0] * esperada.size[1])
        assert distintos < TOLERANCIA, f"{nombre}: {distintos:.2%} de píxeles distintos"


def test_la_cuenta_regresiva_no_mueve_el_foco(configuracion: Configuracion) -> None:
    estado = derivar(Entradas(True, False, True, None, 2, 8, "Sala"), configuracion, "1.0.0")
    resultado = subprocess.run(
        [
            "node",
            str(Path(__file__).with_name("foco.js")),
            str(PLAYWRIGHT),
            str(CHROMIUM),
            str(WEB / "index.html"),
        ],
        input=json.dumps(estado.a_json()),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert resultado.returncode == 0, resultado.stderr
