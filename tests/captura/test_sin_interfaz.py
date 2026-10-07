"""``--sin-interfaz``: the agent runs with no window nor tray, for the API's end-to-end test."""

import logging
import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path

import pytest

from te_tengo_captura import sin_interfaz
from te_tengo_captura.agente import Agente
from te_tengo_captura.backend.cliente import ClienteBackend
from te_tengo_captura.backend.falso import URL_API, BackendFalso
from te_tengo_captura.captura.fuentes import FuenteFalsa, Imagen
from te_tengo_captura.config import Configuracion
from te_tengo_deteccion.pose.schemas import Pose


class SinPersonas:
    def estimar(self, imagen: Imagen, instante_ms: int) -> Pose | None:
        return None

    def reiniciar(self) -> None:
        pass

    def cerrar(self) -> None:
        pass


def crear_agente(tmp_path: Path, configuracion: Configuracion) -> tuple[Agente, BackendFalso]:
    backend = BackendFalso(credencial="cambia-esta-credencial")
    cliente = ClienteBackend(URL_API, backend.credencial, "Sala", "1.0.0", backend.transporte())
    agente = Agente(
        configuracion,
        cliente,
        FuenteFalsa(paso=1 / 8),
        SinPersonas(),
        tmp_path,
        "1.0.0",
        codificar=lambda f: b"mp4",
    )
    return agente, backend


def esperar(prueba: Callable[[], object], limite_s: float = 10) -> None:
    fin = time.monotonic() + limite_s
    while not prueba() and time.monotonic() < fin:
        time.sleep(0.05)


def test_corre_el_agente_sin_ventana_hasta_que_se_detiene(
    tmp_path: Path, configuracion: Configuracion, caplog: pytest.LogCaptureFixture
) -> None:
    agente, backend = crear_agente(tmp_path, configuracion)
    detener = threading.Event()
    caplog.set_level(logging.INFO, logger="te_tengo_captura")

    def detener_al_conectar() -> None:
        # The heartbeat registers the camera and the capture loop opens the source.
        esperar(lambda: backend.senales and agente.bucle.webcam_conectada)
        esperar(lambda: "Estado del agente: enviando" in caplog.text)
        detener.set()

    hilo = threading.Thread(target=detener_al_conectar)
    hilo.start()
    sin_interfaz.ejecutar(agente, detener)
    hilo.join()

    assert backend.registros >= 1
    assert backend.senales
    assert "Estado del agente: enviando" in caplog.text
    assert "Te Tengo Captura detenido" in caplog.text  # agente.detener() ran


def test_registra_solo_los_cambios_de_situacion(
    tmp_path: Path, configuracion: Configuracion, caplog: pytest.LogCaptureFixture
) -> None:
    agente, _ = crear_agente(tmp_path, configuracion)
    registro = sin_interfaz.RegistroDeEstado()
    caplog.set_level(logging.INFO, logger="te_tengo_captura")
    registro(agente.estado())
    registro(agente.estado())
    agente.reintentar_ahora()
    registro(agente.estado())
    assert [m for m in caplog.messages if m.startswith("Estado del agente")] == [
        "Estado del agente: sin_consentimiento",
        "Estado del agente: enviando",
    ]
    agente.detener()


@pytest.mark.skipif(sys.platform == "win32", reason="SIGTERM cannot be sent to itself on Windows")
def test_sigterm_detiene_el_agente(
    tmp_path: Path, configuracion: Configuracion, caplog: pytest.LogCaptureFixture
) -> None:
    agente, _ = crear_agente(tmp_path, configuracion)
    caplog.set_level(logging.INFO, logger="te_tengo_captura")
    anterior = signal.getsignal(signal.SIGTERM)
    threading.Timer(0.5, os.kill, (os.getpid(), signal.SIGTERM)).start()

    sin_interfaz.ejecutar(agente)

    assert "Señal SIGTERM recibida" in caplog.text
    assert signal.getsignal(signal.SIGTERM) == anterior  # the previous handler is restored


def test_no_importa_la_ventana_ni_la_bandeja() -> None:
    codigo = (
        "import sys, te_tengo_captura.__main__, te_tengo_captura.sin_interfaz\n"
        "assert not {'webview', 'pystray'} & set(sys.modules), sorted(sys.modules)\n"
    )
    subprocess.run([sys.executable, "-c", codigo], check=True)
