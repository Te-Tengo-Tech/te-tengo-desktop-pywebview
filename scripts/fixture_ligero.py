"""Writes a light replay file (TTMOV v1) from a movement Parquet file, plus the JSON of what it
decodes to: the golden fixture the app's decoder is tested against (cross-language round trip).

    uv run python scripts/fixture_ligero.py tests/fixtures/clip_caida.parquet \
        tests/fixtures/clip_caida
    uv run python scripts/fixture_ligero.py --z tests/fixtures/clip_caida.parquet \
        tests/fixtures/clip_caida_z

Writes ``<salida>.ttmov`` and ``<salida>.json``. Copy both to the app's ``test/fixtures``.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from te_tengo_captura.almacen.ligero import ArchivoLigero, escribir_ligero, leer_ligero
from te_tengo_captura.almacen.puntos import a_ms, leer_parquet


def esperado(archivo: ArchivoLigero) -> dict[str, Any]:
    """The decoded file as plain JSON (stored integers, not floats)."""
    return {
        "t0Ms": archivo.t0_ms,
        "duracionMs": archivo.duracion_ms,
        "fpsObjetivo": archivo.fps_objetivo,
        "conZ": archivo.con_z,
        "fotogramas": [
            {
                "tMs": f.t_ms,
                "fase": f.fase.value,
                "evento": None if f.evento is None else f.evento.value,
                "x": None if f.x is None else f.x.tolist(),
                "y": None if f.y is None else f.y.tolist(),
                "v": None if f.v is None else f.v.tolist(),
                **({"z": None if f.z is None else f.z.tolist()} if archivo.con_z else {}),
            }
            for f in archivo.fotogramas
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("parquet", type=Path, help="movement file written by Te Tengo Captura")
    parser.add_argument("salida", type=Path, help="output path without extension")
    parser.add_argument("--z", action="store_true", help="include z (the Z flag)")
    args = parser.parse_args()

    metadatos, filas = leer_parquet(args.parquet.read_bytes())
    desde = a_ms(_instante(metadatos["desde"]))
    hasta = a_ms(_instante(metadatos["hasta"]))
    datos = escribir_ligero(filas, desde, hasta, con_z=args.z)
    args.salida.with_suffix(".ttmov").write_bytes(datos)
    texto = json.dumps(esperado(leer_ligero(datos)), separators=(",", ":"))
    args.salida.with_suffix(".json").write_text(texto + "\n", encoding="utf-8")
    print(f"{len(filas)} fotogramas, {len(datos)} bytes → {args.salida}.ttmov")


def _instante(texto: str) -> datetime:
    return datetime.fromisoformat(texto.replace("Z", "+00:00"))


if __name__ == "__main__":
    main()
