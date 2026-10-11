"""JS bridge (pywebview ``js_api``) of the window.

pywebview exposes every public attribute of this object to JavaScript, so the collaborators are
kept in private attributes and only the bridge methods are public. Method names are the
JavaScript ones (camelCase) on purpose.
"""

import base64
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Acciones:
    """The PC link's actions (US-28, US-31); no-ops for an installation."""

    otro_codigo: Callable[[], None] = lambda: None
    vincular_de_nuevo: Callable[[], None] = lambda: None
    ir_a_estado: Callable[[], None] = lambda: None
    desvincular: Callable[[bool], dict[str, bool]] = lambda _borrar: {"ok": False}
    ambientes: Callable[[], list[dict[str, Any]]] = lambda: []
    usar_aqui: Callable[[str, str | None, str | None], dict[str, Any]] = lambda _d, _a, _n: {
        "ok": False
    }
    dejar_de_usar: Callable[[str], dict[str, Any]] = lambda _c: {"ok": False}
    # Advanced mode (US-32 to US-34).
    modo_avanzado: Callable[[bool], bool] = lambda _activar: False
    registro: Callable[[str, int], list[dict[str, Any]]] = lambda _c, _u: []
    medidores: Callable[[str], dict[str, Any] | None] = lambda _c: None
    actividad: Callable[[], list[dict[str, Any]]] = lambda: []
    exportar_diagnostico: Callable[[], dict[str, Any]] = lambda: {"ok": False}
    nombre_diagnostico: Callable[[], str] = lambda: ""
    mostrar_en_carpeta: Callable[[str], None] = lambda _ruta: None


class Puente:
    def __init__(
        self,
        estado: Callable[[], dict[str, Any]],
        ocultar: Callable[[], None],
        buscar_webcam: Callable[[], bool],
        reintentar_ahora: Callable[[], bool],
        vista_previa: Callable[[str], bytes | None] = lambda _clave: None,
        acciones: Acciones | None = None,
    ) -> None:
        self._estado = estado
        self._ocultar = ocultar
        self._buscar_webcam = buscar_webcam
        self._reintentar_ahora = reintentar_ahora
        self._vista_previa = vista_previa
        self._acciones = acciones or Acciones()

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

    def otroCodigo(self) -> None:  # noqa: N802 (JavaScript name)
        """«Mostrar otro código» after «No reconozco esta PC» (D-28.5)."""
        self._acciones.otro_codigo()

    def vincularDeNuevo(self) -> None:  # noqa: N802 (JavaScript name)
        """«Vincular de nuevo» after the PC was removed from the app (D-31.2)."""
        self._acciones.vincular_de_nuevo()

    def irAEstado(self) -> None:  # noqa: N802 (JavaScript name)
        """«Ir a Estado» from «Esta PC quedó vinculada…» (D-28.4)."""
        self._acciones.ir_a_estado()

    def desvincular(self, borrar_datos: bool) -> dict[str, bool]:
        """«Desvincular esta PC», optionally deleting the data saved on it (CA-31.3, CA-31.6)."""
        return self._acciones.desvincular(bool(borrar_datos))

    def ambientes(self) -> list[dict[str, Any]]:
        """The household's rooms for «Elegir aquí, si estás instalando» (CA-29.8)."""
        return self._acciones.ambientes()

    def usarAqui(  # noqa: N802 (JavaScript name)
        self, dispositivo_id: str, ambiente_id: str | None, nombre: str | None
    ) -> dict[str, Any]:
        """«Usar esta cámara» or «Guardar cambio» from this PC."""
        return self._acciones.usar_aqui(
            str(dispositivo_id),
            str(ambiente_id) if ambiente_id else None,
            str(nombre).strip() if nombre else None,
        )

    def dejarDeUsar(self, camara_id: str) -> dict[str, Any]:  # noqa: N802 (JavaScript name)
        """«Dejar de usar» from this PC."""
        return self._acciones.dejar_de_usar(str(camara_id))

    def modoAvanzado(self, activar: bool) -> dict[str, bool]:  # noqa: N802 (JavaScript name)
        """The «Modo avanzado» switch (CA-32.1)."""
        return {"on": self._acciones.modo_avanzado(bool(activar))}

    def registro(self, camara: str, ultimo: int) -> list[dict[str, Any]]:
        """New lines of a camera's live log (CA-32.2)."""
        return self._acciones.registro(str(camara), int(ultimo or 0))

    def medidores(self, camara: str) -> dict[str, Any] | None:
        """A camera's meters (CA-32.3, CA-32.4)."""
        return self._acciones.medidores(str(camara))

    def actividad(self) -> list[dict[str, Any]]:
        """The activity log as the window shows it (US-33)."""
        return self._acciones.actividad()

    def nombreDiagnostico(self) -> str:  # noqa: N802 (JavaScript name)
        return self._acciones.nombre_diagnostico()

    def exportarDiagnostico(self) -> dict[str, Any]:  # noqa: N802 (JavaScript name)
        """«Elegir dónde guardar» and the zip (US-34); ``cancelado`` if no folder was chosen."""
        return self._acciones.exportar_diagnostico()

    def mostrarEnCarpeta(self, ruta: str) -> None:  # noqa: N802 (JavaScript name)
        """«Mostrar en la carpeta»."""
        self._acciones.mostrar_en_carpeta(str(ruta))
