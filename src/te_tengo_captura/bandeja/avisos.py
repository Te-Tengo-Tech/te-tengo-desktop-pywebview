"""When to show a system notification (``osToast`` in the prototype, screens 06, 07 and 09).

* The first time the window is closed or minimized in a session: «sigue funcionando en segundo
  plano», with the text for the current state.
* While the window is closed: a camera stops answering («La cámara de la sala no responde»), or a
  family member starts watching a camera live («Un familiar está viendo la sala en vivo»).
"""

from collections.abc import Callable

from te_tengo_captura.estado import (
    EstadoAgente,
    Notificacion,
    aviso_al_cerrar,
    aviso_camara_desconectada,
    aviso_en_vivo,
)


class Avisos:
    def __init__(self, notificar: Callable[[Notificacion], None]) -> None:
        self._notificar = notificar
        self._ventana_visible = True
        self._ya_se_cerro = False
        self._perdidas: set[str] = set()
        self._en_vivo: set[str] = set()

    def ventana_mostrada(self) -> None:
        self._ventana_visible = True

    def ventana_oculta(self, estado: EstadoAgente) -> None:
        self._ventana_visible = False
        if not self._ya_se_cerro:
            self._ya_se_cerro = True
            self._notificar(aviso_al_cerrar(estado))

    def estado(self, estado: EstadoAgente) -> None:
        camaras = estado.entradas.camaras
        perdidas = {c.clave for c in camaras if not c.webcam_conectada}
        en_vivo = {c.clave for c in camaras if c.en_vivo_desde is not None}
        if not self._ventana_visible:
            for camara in camaras:
                if camara.clave in perdidas - self._perdidas:
                    self._notificar(aviso_camara_desconectada(camara.nombre_habitacion))
                if camara.clave in en_vivo - self._en_vivo:
                    self._notificar(aviso_en_vivo(camara.nombre_habitacion))
        self._perdidas, self._en_vivo = perdidas, en_vivo
