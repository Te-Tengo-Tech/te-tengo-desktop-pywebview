"""Logging: rotating files in the platform log directory, never secrets nor frames.

The code never logs the installation credential, the camera token or upload URLs; as a second
line of defence a filter masks those values if they ever reach a message. Unhandled exceptions
in any thread are logged too, so a crash leaves a trace for the project team.
"""

import logging
import sys
import threading
from collections.abc import Callable, Iterable
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import TracebackType

ARCHIVO = "te-tengo-captura.log"
TAMANO_MAXIMO = 1_000_000  # bytes per file
COPIAS = 5  # te-tengo-captura.log.1 … .5
FORMATO = "%(asctime)s %(levelname)s %(threadName)s %(name)s %(message)s"
OCULTO = "***"


class FiltroSecretos(logging.Filter):
    """Replaces any secret value in a record with ``***``."""

    def __init__(self, secretos: Callable[[], Iterable[str | None]]) -> None:
        super().__init__()
        self._secretos = secretos

    def filter(self, registro: logging.LogRecord) -> bool:
        valores = [s for s in self._secretos() if s and len(s) >= 4]
        if not valores:
            return True
        mensaje = registro.getMessage()
        texto_error = (
            logging.Formatter().formatException(registro.exc_info) if registro.exc_info else None
        )
        limpio = mensaje
        for valor in valores:
            limpio = limpio.replace(valor, OCULTO)
        if limpio != mensaje:
            registro.msg, registro.args = limpio, None
        if texto_error is not None:
            limpio_error = texto_error
            for valor in valores:
                limpio_error = limpio_error.replace(valor, OCULTO)
            if limpio_error != texto_error:
                registro.exc_text, registro.exc_info = limpio_error, None
        return True


def configurar(
    directorio: Path,
    secretos: Callable[[], Iterable[str | None]],
    nivel: int = logging.INFO,
    consola: bool = True,
) -> Path:
    """Sets up the root logger; returns the log file path."""
    directorio.mkdir(parents=True, exist_ok=True)
    ruta = directorio / ARCHIVO
    filtro = FiltroSecretos(secretos)
    manejadores: list[logging.Handler] = [
        RotatingFileHandler(ruta, maxBytes=TAMANO_MAXIMO, backupCount=COPIAS, encoding="utf-8")
    ]
    if consola and sys.stderr is not None:  # a windowed PyInstaller build has no console
        manejadores.append(logging.StreamHandler())
    raiz = logging.getLogger()
    for manejador in list(raiz.handlers):
        raiz.removeHandler(manejador)
        manejador.close()
    for manejador in manejadores:
        manejador.setFormatter(logging.Formatter(FORMATO))
        manejador.addFilter(filtro)
        raiz.addHandler(manejador)
    raiz.setLevel(nivel)
    _capturar_excepciones()
    return ruta


def _capturar_excepciones() -> None:
    def en_proceso(
        tipo: type[BaseException], valor: BaseException, traza: TracebackType | None
    ) -> None:
        logging.getLogger("te_tengo_captura").critical(
            "Error no controlado", exc_info=(tipo, valor, traza)
        )

    def en_hilo(argumentos: threading.ExceptHookArgs) -> None:
        if argumentos.exc_value is None:
            return
        logging.getLogger("te_tengo_captura").critical(
            "Error no controlado en el hilo %s",
            argumentos.thread.name if argumentos.thread else "?",
            exc_info=(argumentos.exc_type, argumentos.exc_value, argumentos.exc_traceback),
        )

    sys.excepthook = en_proceso
    threading.excepthook = en_hilo
