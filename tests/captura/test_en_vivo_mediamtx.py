"""Integration: the live view publishes to a real MediaMTX (skipped without Docker).

MediaMTX runs without authentication (any user may publish, read and use the control API), so
this checks the agent's side only: PyAV's RTSP over TCP publishing of the frames ``Captador``
prepares from ``FuenteFalsa``, and that ``transmitir: false`` ends the stream. Authorization
belongs to the API (``/api/interno/mediamtx/autorizar``).
"""

import json
import shutil
import subprocess
import time
import urllib.request
import uuid
from collections.abc import Iterator
from typing import Any

import pytest

from te_tengo_captura.backend.modelos import ModoVista
from te_tengo_captura.captura.en_vivo import TransmisionEnVivo
from te_tengo_captura.captura.fuentes import Captador, FuenteFalsa

IMAGEN = "bluenviron/mediamtx:1.21.1"
RUTA = "camaras/camara-integracion"

pytestmark = pytest.mark.docker


def _docker_disponible() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        return subprocess.run(["docker", "info"], capture_output=True, timeout=20).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _docker(*argumentos: str, timeout: float = 30) -> str:
    resultado = subprocess.run(
        ["docker", *argumentos], capture_output=True, text=True, timeout=timeout, check=True
    )
    return resultado.stdout.strip()


def _puerto(nombre: str, interno: int) -> int:
    # "127.0.0.1:49153" (one line per address family)
    return int(_docker("port", nombre, f"{interno}/tcp").splitlines()[0].rsplit(":", 1)[1])


class MediaMTX:
    def __init__(self, nombre: str) -> None:
        self.nombre = nombre
        self.rtsp = _puerto(nombre, 8554)
        self.api = _puerto(nombre, 9997)

    def rutas(self) -> list[dict[str, Any]]:
        url = f"http://127.0.0.1:{self.api}/v3/paths/list"
        with urllib.request.urlopen(url, timeout=2) as respuesta:
            items: list[dict[str, Any]] = json.load(respuesta)["items"]
            return items

    def lista(self, ruta: str) -> dict[str, Any] | None:
        return next((r for r in self.rutas() if r["name"] == ruta and r["ready"]), None)

    def esperar_api(self, limite_s: float = 20) -> None:
        fin = time.monotonic() + limite_s
        while True:
            try:
                self.rutas()
                return
            except OSError:
                if time.monotonic() > fin:
                    raise
                time.sleep(0.2)


@pytest.fixture(scope="module")
def mediamtx() -> Iterator[MediaMTX]:
    if not _docker_disponible():
        pytest.skip("Docker no está disponible")
    nombre = f"te-tengo-mediamtx-{uuid.uuid4().hex[:8]}"
    permisos = {
        f"MTX_AUTHINTERNALUSERS_0_PERMISSIONS_{i}_ACTION": accion
        for i, accion in enumerate(("publish", "read", "api"))
    }
    entorno = [f"--env={k}={v}" for k, v in {"MTX_API": "yes", **permisos}.items()]
    _docker("pull", "--quiet", IMAGEN, timeout=300)
    _docker(
        "run",
        "--detach",
        "--rm",
        f"--name={nombre}",
        "--publish=127.0.0.1::8554",
        "--publish=127.0.0.1::9997",
        "--env=MTX_AUTHINTERNALUSERS_0_USER=any",
        *entorno,
        IMAGEN,
    )
    try:
        servidor = MediaMTX(nombre)
        servidor.esperar_api()
        yield servidor
    finally:
        subprocess.run(["docker", "rm", "--force", nombre], capture_output=True, timeout=30)


def test_publica_la_vista_en_vivo_en_mediamtx(mediamtx: MediaMTX) -> None:
    vivo = TransmisionEnVivo(permitida=lambda: True)
    vivo.iniciar()
    captador = Captador(FuenteFalsa(paso=1 / 8))
    try:
        vivo.transmitir(
            f"rtsp://127.0.0.1:{mediamtx.rtsp}/{RUTA}", "agente", "sin-auth", ModoVista.VIDEO
        )
        ruta = None
        fin = time.monotonic() + 15
        while time.monotonic() < fin:
            if (fotograma := captador.leer()) is not None:
                vivo.enviar(fotograma, None)
            if vivo.publicados >= 24 and (ruta := mediamtx.lista(RUTA)) is not None:
                break
            time.sleep(1 / 8)
        assert ruta is not None, mediamtx.rutas()
        assert ruta["tracks"] == ["H264"]
        assert ruta["source"]["type"] == "rtspSession"

        vivo.detener()  # {"transmitir": false}
        fin = time.monotonic() + 5
        while mediamtx.lista(RUTA) is not None and time.monotonic() < fin:
            time.sleep(0.2)
        assert mediamtx.lista(RUTA) is None
    finally:
        vivo.cerrar()
