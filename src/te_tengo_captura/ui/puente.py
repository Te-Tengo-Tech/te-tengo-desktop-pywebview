"""JS bridge (pywebview ``js_api``) of the window.

pywebview exposes every public attribute of this object to JavaScript, so the collaborators are
kept in private attributes and only the bridge methods are public. Method names are the
JavaScript ones (camelCase) on purpose.
"""

import base64
from collections.abc import Callable
from typing import Any


class Puente:
    def __init__(
        self,
        estado: Callable[[], dict[str, Any]],
        ocultar: Callable[[], None],
        buscar_webcam: Callable[[], bool],
        reintentar_ahora: Callable[[], bool],
        vista_previa: Callable[[str], bytes | None] = lambda _clave: None,
    ) -> None:
        self._estado = estado
        self._ocultar = ocultar
        self._buscar_webcam = buscar_webcam
        self._reintentar_ahora = reintentar_ahora
        self._vista_previa = vista_previa

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

    def vistaPrevia(self, clave: str) -> dict[str, str | None]:  # noqa: N802 (JavaScript name)
        """The newest frame of a camera as base64 JPEG, only for this window (CA-29.8)."""
        jpeg = self._vista_previa(str(clave))
        return {"jpeg": base64.b64encode(jpeg).decode("ascii") if jpeg else None}
