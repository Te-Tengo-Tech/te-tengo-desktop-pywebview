"""The PC's activity log (US-33): who changed what and when, also offline.

Every change made on this PC is appended to ``actividad.jsonl`` in the data folder (append-only:
nothing is ever edited or deleted, CA-33.1) with a UUID v7 ``id`` and the time it happened. The
changes the API does not see on its own (contract: ``MODO_AVANZADO_ACTIVADO``/``_DESACTIVADO``,
``GUARDADO_LOCAL_CAMBIADO``, ``DATOS_LOCALES_ELIMINADOS``) are sent to
``POST /api/agente/pc/actividad`` in batches of at most 100; until the API answers they show
«Pendiente de enviar» (CA-33.3). Sending the same ``id`` again is safe (``repetidos``). The ids
the API acknowledged go to ``actividad-enviada.txt``, also append-only.

The window also lists what this PC heard from the app on its channel (a camera chosen or no
longer used), as the prototype's «Actividad» does. An installation has no PC token: its entries
are kept locally only. The household's whole log (``GET /api/actividad``) needs a member's token
the PC does not have (``docs/BLOCKERS.md``).
"""

import json
import logging
import threading
from collections.abc import Callable
from datetime import UTC, datetime, tzinfo
from pathlib import Path
from typing import Any, Protocol

from te_tengo_captura.backend.errores import ErrorBackendError
from te_tengo_captura.backend.modelos import iso_utc
from te_tengo_captura.ids import uuid7

logger = logging.getLogger(__name__)

ARCHIVO = "actividad.jsonl"
ARCHIVO_ENVIADOS = "actividad-enviada.txt"
LOTE = 100  # contract: at most 100 changes per request
CAMPOS = ("id", "tipo", "ocurridoEn", "objeto", "valorAnterior", "valorNuevo")
TIPOS_DE_LA_PC = frozenset(
    {
        "MODO_AVANZADO_ACTIVADO",
        "MODO_AVANZADO_DESACTIVADO",
        "GUARDADO_LOCAL_CAMBIADO",
        "DATOS_LOCALES_ELIMINADOS",
    }
)


class RemitenteActividad(Protocol):
    def actividad(self, cambios: list[dict[str, Any]]) -> None: ...


class RegistroActividad:
    def __init__(
        self,
        directorio: Path,
        reloj_utc: Callable[[], datetime] = lambda: datetime.now(UTC),
        generar_id: Callable[[], str] = uuid7,
    ) -> None:
        self._ruta = directorio / ARCHIVO
        self._ruta_enviados = directorio / ARCHIVO_ENVIADOS
        self._reloj_utc = reloj_utc
        self._generar_id = generar_id
        self._candado = threading.Lock()

    def anotar(
        self,
        texto: str,
        tipo: str | None = None,
        objeto: str | None = None,
        anterior: str | None = None,
        nuevo: str | None = None,
        quien: str = "pc",
    ) -> dict[str, Any]:
        """Appends a change. ``tipo`` (one of ``TIPOS_DE_LA_PC``) makes it go to the API;
        ``quien`` is ``pc`` («Desde esta PC») or a family member's initials."""
        entrada: dict[str, Any] = {
            "id": self._generar_id(),
            "ocurridoEn": iso_utc(self._reloj_utc()),
            "texto": texto,
            "quien": quien,
        }
        if tipo is not None:
            entrada["tipo"] = tipo
            for campo, valor in (
                ("objeto", objeto),
                ("valorAnterior", anterior),
                ("valorNuevo", nuevo),
            ):
                if valor is not None:
                    entrada[campo] = valor[:200] if campo != "objeto" else valor[:120]
        with self._candado:
            try:
                self._ruta.parent.mkdir(parents=True, exist_ok=True)
                with self._ruta.open("a", encoding="utf-8") as archivo:
                    archivo.write(json.dumps(entrada, ensure_ascii=False) + "\n")
            except OSError as error:
                logger.warning("No se pudo anotar la actividad: %s", error)
        logger.info("Actividad: %s", texto)
        return entrada

    def entradas(self) -> list[dict[str, Any]]:
        """Every entry, newest first, with ``pendiente`` for those the API has not heard yet."""
        with self._candado:
            todas = self._leer()
            enviados = self._enviados()
        for entrada in todas:
            entrada["pendiente"] = "tipo" in entrada and entrada["id"] not in enviados
        return list(reversed(todas))

    def pendientes(self) -> list[dict[str, Any]]:
        with self._candado:
            enviados = self._enviados()
            return [e for e in self._leer() if "tipo" in e and e["id"] not in enviados]

    def enviar(self, remitente: RemitenteActividad) -> int:
        """Sends what is pending, oldest first; returns how many the API acknowledged."""
        enviados = 0
        while pendientes := self.pendientes()[:LOTE]:
            cambios: list[dict[str, Any]] = [
                {
                    k: e[k]
                    for k in ("id", "tipo", "ocurridoEn", "objeto", "valorAnterior", "valorNuevo")
                    if k in e
                }
                for e in pendientes
            ]
            try:
                remitente.actividad(cambios)
            except ErrorBackendError as error:
                logger.info("Actividad pendiente de enviar (%d): %s", len(cambios), error)
                if not error.reintentable:
                    logger.warning("La API rechazó la actividad: %s", error)
                break
            with self._candado:
                try:
                    with self._ruta_enviados.open("a", encoding="utf-8") as archivo:
                        archivo.writelines(c["id"] + "\n" for c in cambios)
                except OSError as error:
                    logger.warning("No se pudo anotar la actividad enviada: %s", error)
                    break
            enviados += len(cambios)
        return enviados

    def _leer(self) -> list[dict[str, Any]]:
        try:
            lineas = self._ruta.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            return []
        except OSError:
            return []
        entradas = []
        for linea in lineas:
            try:
                entrada = json.loads(linea)
            except ValueError:
                continue
            if isinstance(entrada, dict) and "id" in entrada:
                entradas.append(entrada)
        return entradas

    def _enviados(self) -> set[str]:
        try:
            return set(self._ruta_enviados.read_text(encoding="utf-8").split())
        except OSError:
            return set()


def para_la_ventana(
    entradas: list[dict[str, Any]], zona: tzinfo | None = None, hoy: datetime | None = None
) -> list[dict[str, Any]]:
    """Groups the entries by day as the prototype does («Hoy», «Ayer · 22/09/2026», a date)."""
    hoy_local = (hoy or datetime.now(UTC)).astimezone(zona).date()
    filas = []
    for entrada in entradas:
        try:
            momento = datetime.fromisoformat(
                entrada["ocurridoEn"].replace("Z", "+00:00")
            ).astimezone(zona)
        except (KeyError, ValueError):
            continue
        dias = (hoy_local - momento.date()).days
        dia = (
            "Hoy"
            if dias == 0
            else f"Ayer · {momento:%d/%m/%Y}"
            if dias == 1
            else f"{momento:%d/%m/%Y}"
        )
        filas.append(
            {
                "d": dia,
                "t": f"{momento:%H:%M}",
                "m": entrada.get("texto", ""),
                "who": entrada.get("quien", "pc"),
                "pend": bool(entrada.get("pendiente")),
                "scope": "pc",
            }
        )
    return filas
