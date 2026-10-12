"""«Exportar diagnóstico» (US-34): logs, version and thresholds; no secrets, images or landmarks."""

import json
import zipfile
from datetime import date
from pathlib import Path

import pytest

from te_tengo_captura.diagnostico import exportar, nombre_archivo


def test_nombre_del_archivo() -> None:
    assert (
        nombre_archivo("Sala-Rosa", date(2026, 9, 23))
        == "te-tengo-diagnostico-Sala-Rosa-2026-09-23.zip"
    )
    assert (
        nombre_archivo("PC de la casa/1", date(2026, 9, 23))
        == "te-tengo-diagnostico-PC-de-la-casa-1-2026-09-23.zip"
    )


def test_contenido_sin_datos_privados(tmp_path: Path) -> None:
    registros = tmp_path / "logs"
    registros.mkdir()
    (registros / "te-tengo-captura.log").write_text(
        "INFO token acceso-secreto-123 visto\n", encoding="utf-8"
    )
    (registros / "te-tengo-captura.log.1").write_text("INFO anterior\n", encoding="utf-8")
    (registros / "foto.jpg").write_bytes(b"\xff\xd8")
    destino = tmp_path / "diag.zip"
    datos = {
        "programa": "Te Tengo Captura 0.5.0",
        "camaras": [{"habitacion": "Sala", "umbrales": {"velocidad_descenso_min": 0.01}}],
    }
    tamano = exportar(destino, registros, datos, ["acceso-secreto-123"])
    assert tamano == destino.stat().st_size
    with zipfile.ZipFile(destino) as archivo:
        nombres = sorted(archivo.namelist())
        assert nombres == [
            "diagnostico.json",
            "registros/te-tengo-captura.log",
            "registros/te-tengo-captura.log.1",
        ]
        assert "acceso-secreto-123" not in archivo.read("registros/te-tengo-captura.log").decode()
        assert json.loads(archivo.read("diagnostico.json"))["camaras"][0]["habitacion"] == "Sala"


def test_sin_archivo_a_medias_si_falla(tmp_path: Path) -> None:
    carpeta = tmp_path / "solo-lectura"
    carpeta.mkdir()
    carpeta.chmod(0o500)
    try:
        with pytest.raises(PermissionError):
            exportar(carpeta / "diag.zip", tmp_path, {}, [])
        assert list(carpeta.iterdir()) == []
    finally:
        carpeta.chmod(0o700)
