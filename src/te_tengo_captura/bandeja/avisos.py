"""When to show a system notification (``osToast`` in the prototype, screens 06, 07 and 09).

* The first time the window is closed or minimized in a session: «sigue funcionando en segundo
  plano», with the text for the current state.
* While the window is closed: a camera stops answering («La cámara de la sala no responde»), a
  family member starts watching a camera live («Un familiar está viendo la sala en vivo»), or the
  PC was removed from the household in the app («Esta PC se quitó de la vivienda», D-31.2).
* A new version of the program (US-43, screen 67): «Hay una versión nueva: X», once per version
  (``marcar`` remembers the version across restarts) and only while the window is closed; with
  the window open the band says it and the version counts as announced. While an alert or a live
  view is open the notice waits (CA-43.9: the caller passes no version then).
"""

from collections.abc import Callable
from typing import Protocol

from te_tengo_captura.estado import (
    EstadoAgente,
    Notificacion,
    aviso_al_cerrar,
    aviso_camara_desconectada,
    aviso_en_vivo,
    aviso_pc_quitada,
    aviso_sin_vincular,
    aviso_version_nueva,
)


class EstadoMostrado(Protocol):
    """What the coordinator publishes (``coordinador.EstadoVentana``)."""

    @property
    def agente(self) -> EstadoAgente | None: ...

    @property
    def quitada(self) -> bool: ...

    def a_json(self) -> dict[str, object]: ...


class Avisos:
    def __init__(self, notificar: Callable[[Notificacion], None]) -> None:
        self._notificar = notificar
        self._ventana_visible = True
        self._ya_se_cerro = False
        self._perdidas: set[str] = set()
        self._en_vivo: set[str] = set()
        self._quitada = False

    def ventana_mostrada(self) -> None:
        self._ventana_visible = True

    def ventana_oculta(self, estado: EstadoMostrado) -> None:
        self._ventana_visible = False
        if not self._ya_se_cerro:
            self._ya_se_cerro = True
            agente = estado.agente
            self._notificar(
                aviso_al_cerrar(agente)
                if agente is not None and estado.a_json().get("screen") == "main"
                else aviso_sin_vincular(agente)
            )

    def version_nueva(self, version: str | None, mac: bool, marcar: Callable[[str], bool]) -> None:
        """``version``: a new version that may be announced now (``None``: none, or it waits)."""
        if version is None:
            return
        if marcar(version) and not self._ventana_visible:
            self._notificar(aviso_version_nueva(version, mac))

    def estado(self, estado: EstadoMostrado) -> None:
        if estado.quitada and not self._quitada and not self._ventana_visible:
            self._notificar(aviso_pc_quitada(str(estado.a_json().get("at", ""))))
        self._quitada = estado.quitada
        agente = estado.agente
        if agente is None:
            self._perdidas, self._en_vivo = set(), set()
            return
        camaras = agente.entradas.camaras
        perdidas = {c.clave for c in camaras if not c.webcam_conectada}
        en_vivo = {c.clave for c in camaras if c.en_vivo_desde is not None}
        if not self._ventana_visible:
            for camara in camaras:
                if camara.clave in perdidas - self._perdidas:
                    self._notificar(aviso_camara_desconectada(camara.nombre_habitacion))
                if camara.clave in en_vivo - self._en_vivo:
                    self._notificar(aviso_en_vivo(camara.nombre_habitacion))
        self._perdidas, self._en_vivo = perdidas, en_vivo
