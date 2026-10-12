"""The PC's activity log (US-33): append-only, pending while offline, sent once."""

import json
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from te_tengo_captura.actividad import RegistroActividad, para_la_ventana
from te_tengo_captura.backend.errores import SinConexionError

LIMA = timezone(timedelta(hours=-5))


class Remitente:
    def __init__(self) -> None:
        self.lotes: list[list[dict[str, Any]]] = []
        self.sin_conexion = False

    def actividad(self, cambios: list[dict[str, Any]]) -> None:
        if self.sin_conexion:
            raise SinConexionError("sin internet")
        self.lotes.append(cambios)


@pytest.fixture
def registro(tmp_path: Path) -> RegistroActividad:
    ahora = datetime(2026, 9, 23, 15, 42, tzinfo=UTC)
    return RegistroActividad(tmp_path, reloj_utc=lambda: ahora)


def test_pendiente_de_enviar_hasta_que_vuelve_internet(registro: RegistroActividad) -> None:
    registro.anotar("Desde esta PC: se activó el modo avanzado", tipo="MODO_AVANZADO_ACTIVADO")
    registro.anotar(
        "La familia eligió desde la app la Logitech C920 para el Dormitorio", quien="app"
    )
    remitente = Remitente()
    remitente.sin_conexion = True
    assert registro.enviar(remitente) == 0
    entradas = registro.entradas()
    assert [e["pendiente"] for e in entradas] == [False, True]  # newest first; only the PC's own
    remitente.sin_conexion = False
    assert registro.enviar(remitente) == 1
    assert remitente.lotes[0][0]["tipo"] == "MODO_AVANZADO_ACTIVADO"
    assert remitente.lotes[0][0]["ocurridoEn"] == "2026-09-23T15:42:00.000Z"
    assert set(remitente.lotes[0][0]) == {"id", "tipo", "ocurridoEn"}
    assert not any(e["pendiente"] for e in registro.entradas())
    assert registro.enviar(remitente) == 0  # sent once


def test_una_repeticion_vista_lleva_la_camara_el_momento_y_la_duracion(
    registro: RegistroActividad,
) -> None:
    """CA-39.3: a replay watched on this PC goes to the family's log as ``REPETICION_VISTA``."""
    registro.anotar(
        "Desde esta PC: se vio qué pasó en la Sala (23/09 10:36–10:46, 3 min)",
        tipo="REPETICION_VISTA",
        objeto="Sala",
        datos={
            "camaraId": "c1",
            "momentoDesde": "2026-09-23T15:36:00.000Z",
            "momentoHasta": "2026-09-23T15:46:00.000Z",
            "duracionSegundos": 180,
            "otro": "no se envía",
        },
    )
    remitente = Remitente()
    assert registro.enviar(remitente) == 1
    [cambio] = remitente.lotes[0]
    assert cambio["tipo"] == "REPETICION_VISTA"
    assert cambio["objeto"] == "Sala"
    assert cambio["camaraId"] == "c1"
    assert (cambio["momentoDesde"], cambio["momentoHasta"]) == (
        "2026-09-23T15:36:00.000Z",
        "2026-09-23T15:46:00.000Z",
    )
    assert cambio["duracionSegundos"] == 180
    assert "otro" not in cambio
    assert "texto" not in cambio  # the window's sentence stays on this PC


def test_lotes_de_cien(registro: RegistroActividad) -> None:
    for i in range(230):
        registro.anotar(
            f"cambio {i}",
            tipo="GUARDADO_LOCAL_CAMBIADO",
            objeto="Video continuo",
            anterior="No",
            nuevo="Sí, 7 días",
        )
    remitente = Remitente()
    assert registro.enviar(remitente) == 230
    assert [len(lote) for lote in remitente.lotes] == [100, 100, 30]
    assert remitente.lotes[0][0]["valorNuevo"] == "Sí, 7 días"


def test_solo_se_agrega(registro: RegistroActividad, tmp_path: Path) -> None:
    registro.anotar("uno")
    registro.anotar("dos")
    lineas = (tmp_path / "actividad.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(linea)["texto"] for linea in lineas] == ["uno", "dos"]
    ids = [json.loads(linea)["id"] for linea in lineas]
    assert len(set(ids)) == 2


def test_agrupada_por_dia_para_la_ventana() -> None:
    hoy = datetime(2026, 9, 23, 15, 42, tzinfo=UTC)
    entradas: list[dict[str, Any]] = [
        {
            "id": "a",
            "ocurridoEn": "2026-09-23T15:31:00.000Z",
            "texto": "Carmen vinculó la PC Sala-Rosa",
            "quien": "CH",
        },
        {
            "id": "b",
            "ocurridoEn": "2026-09-22T23:05:00.000Z",
            "texto": "ayer",
            "quien": "pc",
            "pendiente": True,
        },
        {"id": "c", "ocurridoEn": "2026-09-10T15:00:00.000Z", "texto": "antes"},
    ]
    filas = para_la_ventana(entradas, LIMA, hoy)
    assert [(f["d"], f["t"], f["who"], f["pend"]) for f in filas] == [
        ("Hoy", "10:31", "CH", False),
        ("Ayer · 22/09/2026", "18:05", "pc", True),
        ("10/09/2026", "10:00", "pc", False),
    ]
