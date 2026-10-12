"""«Exportar diagnóstico» (US-34): a zip for the support team, without private data.

It holds the program's logs (already written without secrets, and checked again here), the
version, the operating system, the cameras with their rooms and the thresholds in force
(CA-34.1). It never holds credentials or tokens, images, video or body landmarks (CA-34.2). The
zip is written to a temporary file next to the destination and renamed when complete, so a full
disk or a folder that does not allow writing leaves no half file (CA-34.3).
"""

import json
import os
import re
import zipfile
from datetime import date
from pathlib import Path
from typing import Any

OCULTO = "***"


def nombre_archivo(nombre_pc: str, dia: date) -> str:
    """``te-tengo-diagnostico-Sala-Rosa-2026-09-23.zip`` (the prototype's name)."""
    pc = re.sub(r"[^A-Za-z0-9_-]+", "-", nombre_pc).strip("-") or "PC"
    return f"te-tengo-diagnostico-{pc}-{dia.isoformat()}.zip"


def exportar(destino: Path, registros: Path, datos: dict[str, Any], secretos: list[str]) -> int:
    """Writes the zip at ``destino``; returns its size in bytes. Raises ``OSError`` on failure
    with nothing left behind."""
    temporal = destino.with_name(f".{destino.name}.{os.getpid()}.tmp")
    valores = [s for s in secretos if s and len(s) >= 4]
    try:
        with zipfile.ZipFile(temporal, "w", compression=zipfile.ZIP_DEFLATED) as archivo:
            archivo.writestr(
                "diagnostico.json", json.dumps(datos, ensure_ascii=False, indent=2, default=str)
            )
            for registro in sorted(registros.glob("te-tengo-captura.log*")):
                texto = registro.read_text(encoding="utf-8", errors="replace")
                for valor in valores:
                    texto = texto.replace(valor, OCULTO)
                archivo.writestr(f"registros/{registro.name}", texto)
        os.replace(temporal, destino)
    except BaseException:
        temporal.unlink(missing_ok=True)
        raise
    return destino.stat().st_size
