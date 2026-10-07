import logging
import sys
import threading
from collections.abc import Iterator
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

from te_tengo_captura import registro

SECRETO = "credencial-super-secreta"


@pytest.fixture(autouse=True)
def restaurar_logging() -> Iterator[None]:
    raiz = logging.getLogger()
    manejadores, nivel = list(raiz.handlers), raiz.level
    ganchos = (sys.excepthook, threading.excepthook)
    yield
    for manejador in list(raiz.handlers):
        raiz.removeHandler(manejador)
        manejador.close()
    for manejador in manejadores:
        raiz.addHandler(manejador)
    raiz.setLevel(nivel)
    sys.excepthook, threading.excepthook = ganchos


def leer(ruta: Path) -> str:
    for manejador in logging.getLogger().handlers:
        manejador.flush()
    return ruta.read_text(encoding="utf-8")


def test_archivo_rotativo_en_el_directorio_de_logs(tmp_path: Path) -> None:
    ruta = registro.configurar(tmp_path / "logs", lambda: [], consola=False)
    assert ruta == tmp_path / "logs" / "te-tengo-captura.log"
    (archivo,) = logging.getLogger().handlers
    assert isinstance(archivo, RotatingFileHandler)
    assert (archivo.maxBytes, archivo.backupCount) == (1_000_000, 5)
    logging.getLogger("te_tengo_captura.prueba").info("Evento detectado: caida")
    assert "INFO MainThread te_tengo_captura.prueba Evento detectado: caida" in leer(ruta)


def test_nunca_escribe_secretos(tmp_path: Path) -> None:
    ruta = registro.configurar(tmp_path, lambda: [SECRETO, "token-7", None, ""], consola=False)
    log = logging.getLogger("te_tengo_captura.prueba")
    log.warning("credencial %s y token %s", SECRETO, "token-7")
    try:
        raise RuntimeError(f"falló con {SECRETO}")
    except RuntimeError:
        log.exception("Error")
    texto = leer(ruta)
    assert SECRETO not in texto
    assert "token-7" not in texto
    assert "credencial *** y token ***" in texto
    assert "RuntimeError: falló con ***" in texto


def test_errores_no_controlados_en_hilos_quedan_registrados(tmp_path: Path) -> None:
    ruta = registro.configurar(tmp_path, lambda: [], consola=False)

    def fallar() -> None:
        raise ValueError("fallo en el hilo")

    hilo = threading.Thread(target=fallar, name="captura")
    hilo.start()
    hilo.join()
    sys.excepthook(KeyError, KeyError("fallo del proceso"), None)
    texto = leer(ruta)
    assert "Error no controlado en el hilo captura" in texto
    assert "ValueError: fallo en el hilo" in texto
    assert "Error no controlado" in texto
    assert "KeyError" in texto


def test_con_consola(tmp_path: Path) -> None:
    registro.configurar(tmp_path, lambda: [])
    assert len(logging.getLogger().handlers) == 2
