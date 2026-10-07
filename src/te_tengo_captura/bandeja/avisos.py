"""When to show a system notification (``osToast`` in the prototype, screens 06 and 07).

* The first time the window is closed or minimized in a session: «sigue funcionando en segundo
  plano», with the text for the current state.
* When the webcam disconnects while the window is closed: «La webcam se desconectó».
"""

from collections.abc import Callable

from te_tengo_captura.config import Configuracion
from te_tengo_captura.estado import (
    EstadoAgente,
    Notificacion,
    Situacion,
    aviso_al_cerrar,
    aviso_webcam_desconectada,
)


class Avisos:
    def __init__(self, config: Configuracion, notificar: Callable[[Notificacion], None]) -> None:
        self._config = config
        self._notificar = notificar
        self._ventana_visible = True
        self._ya_se_cerro = False
        self._webcam_perdida = False

    def ventana_mostrada(self) -> None:
        self._ventana_visible = True

    def ventana_oculta(self, estado: EstadoAgente) -> None:
        self._ventana_visible = False
        if not self._ya_se_cerro:
            self._ya_se_cerro = True
            self._notificar(aviso_al_cerrar(estado))

    def estado(self, estado: EstadoAgente) -> None:
        perdida = estado.situacion is Situacion.WEBCAM_DESCONECTADA
        if perdida and not self._webcam_perdida and not self._ventana_visible:
            self._notificar(aviso_webcam_desconectada(self._config))
        self._webcam_perdida = perdida
