"""JS bridge (pywebview ``js_api``) of the status window.

pywebview exposes every public attribute of this object to JavaScript, so the collaborators are
kept in private attributes and only the five bridge methods are public. Method names are the
JavaScript ones (camelCase) on purpose.
"""

from collections.abc import Callable
from typing import Any


class Puente:
    def __init__(
        self,
        estado: Callable[[], dict[str, Any]],
        ocultar: Callable[[], None],
        buscar_webcam: Callable[[], bool],
        reintentar_ahora: Callable[[], bool],
    ) -> None:
        self._estado = estado
        self._ocultar = ocultar
        self._buscar_webcam = buscar_webcam
        self._reintentar_ahora = reintentar_ahora

    def estado(self) -> dict[str, Any]:
        """The current state, for the first render (later ones are pushed by Python)."""
        return self._estado()

    def minimizar(self) -> None:
        """Minimize hides to the tray; the agent keeps running."""
        self._ocultar()

    def cerrar(self) -> None:
        """Close hides to the tray too: it never stops the agent."""
        self._ocultar()

    def buscarWebcam(self) -> dict[str, bool]:  # noqa: N802 (JavaScript name)
        """«Buscar de nuevo»: reopen the webcam; ``ok`` tells whether it answered."""
        return {"ok": self._buscar_webcam()}

    def reintentarAhora(self) -> dict[str, bool]:  # noqa: N802 (JavaScript name)
        """«Reintentar ahora»: heartbeat and outbox at once; ``ok`` tells whether it connected."""
        return {"ok": self._reintentar_ahora()}
