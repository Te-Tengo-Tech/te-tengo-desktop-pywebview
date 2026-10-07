"""Single instance: a second launch shows the running agent's window instead of starting again.

The first instance holds an exclusive OS lock on ``instancia.lock`` in the data directory (the
OS releases it if the process dies) and listens on a loopback socket on a random port. The port
and a random token are written to ``instancia.json``. A second launch fails to take the lock,
sends the token to that port and exits; the first instance then shows its window.
"""

import json
import logging
import secrets
import socket
import sys
import threading
from collections.abc import Callable
from pathlib import Path
from typing import IO

logger = logging.getLogger(__name__)

MENSAJE = "mostrar"


def _bloquear(archivo: IO[str]) -> bool:
    archivo.seek(0)
    try:
        if sys.platform == "win32":
            import msvcrt

            msvcrt.locking(archivo.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(archivo.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False
    return True


class Instancia:
    def __init__(self, directorio: Path) -> None:
        self._directorio = directorio
        self._candado: IO[str] | None = None
        self._servidor: socket.socket | None = None
        self._token = secrets.token_hex(16)

    def adquirir(self, al_mostrar: Callable[[], None]) -> bool:
        """``True`` if this is the only instance; then ``al_mostrar`` runs on each relaunch."""
        self._directorio.mkdir(parents=True, exist_ok=True)
        archivo = (self._directorio / "instancia.lock").open("a+", encoding="utf-8")
        if not _bloquear(archivo):
            archivo.close()
            return False
        self._candado = archivo
        servidor = socket.create_server(("127.0.0.1", 0))
        self._servidor = servidor
        datos = {"puerto": servidor.getsockname()[1], "token": self._token}
        (self._directorio / "instancia.json").write_text(json.dumps(datos), encoding="utf-8")
        threading.Thread(
            target=self._escuchar, args=(servidor, al_mostrar), name="instancia", daemon=True
        ).start()
        return True

    def avisar(self, espera_s: float = 2.0) -> bool:
        """From a second launch: ask the running instance to show its window."""
        try:
            datos = json.loads((self._directorio / "instancia.json").read_text(encoding="utf-8"))
            with socket.create_connection(("127.0.0.1", int(datos["puerto"])), espera_s) as c:
                c.sendall(f"{datos['token']} {MENSAJE}\n".encode())
                return c.recv(16).strip() == b"ok"
        except (OSError, ValueError, KeyError) as error:
            logger.warning("No se pudo avisar a la instancia en ejecución: %s", error)
            return False

    def liberar(self) -> None:
        if self._servidor is not None:
            self._servidor.close()
            self._servidor = None
        if self._candado is not None:
            self._candado.close()
            self._candado = None

    def _escuchar(self, servidor: socket.socket, al_mostrar: Callable[[], None]) -> None:
        while True:
            try:
                conexion, _ = servidor.accept()
            except OSError:
                return  # closed by liberar()
            with conexion:
                conexion.settimeout(2.0)
                try:
                    linea = conexion.recv(256).decode(errors="replace").strip()
                except OSError:
                    continue
                if linea == f"{self._token} {MENSAJE}":
                    conexion.sendall(b"ok\n")
                    al_mostrar()
