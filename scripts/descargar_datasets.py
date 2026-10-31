"""Downloads the public fall datasets used in the validation (they are not versioned).

* URFD (Kwolek and Kepski, 2014): 30 falls and 40 activities of daily living. The video from
  camera 0 (parallel to the floor) and the per-frame labels are downloaded. License CC BY-NC-SA
  4.0. https://fenix.ur.edu.pl/~mkepski/ds/uf.html
* CAUCAFall (Eraso Guerrero et al., 2022): 10 people × (5 falls + 5 activities) in a home.
  Only the .avi video of each activity is downloaded. License CC BY 4.0.
  https://doi.org/10.17632/7w7fccy7ky.4
* GMDCSA24 v2.1 (Alam et al., 2024): 4 people, 79 falls and 81 activities of daily living in
  3 rooms, recorded with a laptop webcam (720p or 480p, 15 or 30 fps). Only for the hold-out
  test (docs/validation.md, section 6): it is never used to calibrate the shipped thresholds.
  The 1.1 GB Zenodo zip is checked against its MD5 and only the .mp4, .csv, README and LICENSE
  files are extracted. License CC BY 4.0 (Zenodo record; the GitHub copy says MIT).
  https://doi.org/10.5281/zenodo.13354453

Usage: uv run python scripts/descargar_datasets.py [--destino datos] [--datasets urfd caucafall
gmdcsa24]
"""

import argparse
import hashlib
import json
import shutil
import sys
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

URFD = "https://fenix.ur.edu.pl/~mkepski/ds/data"
MENDELEY = "https://data.mendeley.com/public-api/datasets/7w7fccy7ky"
VERSION_CAUCAFALL = 4
ZENODO_GMDCSA24 = (
    "https://zenodo.org/api/records/13354453/files/"
    "ekramalam/GMDCSA24-A-Dataset-for-Human-Fall-Detection-in-Videos-v2.1.zip/content"
)
MD5_GMDCSA24 = "3d36f2c5c1a666b99639e4e9fd843efb"
EXTRAER_GMDCSA24 = (".mp4", ".csv", "README.md", "LICENSE")
CABECERAS = {"User-Agent": "Mozilla/5.0 (te-tengo-validacion)"}


def bajar(url: str, destino: Path) -> str:
    if destino.exists() and destino.stat().st_size > 0:
        return f"ya existe {destino}"
    destino.parent.mkdir(parents=True, exist_ok=True)
    pedido = urllib.request.Request(url, headers=CABECERAS)
    with urllib.request.urlopen(pedido, timeout=120) as respuesta:
        temporal = destino.with_suffix(destino.suffix + ".parcial")
        with temporal.open("wb") as archivo:
            shutil.copyfileobj(respuesta, archivo, 1 << 20)
        temporal.rename(destino)
    return f"descargado {destino}"


def leer_json(url: str) -> list[dict[str, object]]:
    with urllib.request.urlopen(
        urllib.request.Request(url, headers=CABECERAS), timeout=60
    ) as respuesta:
        datos: list[dict[str, object]] = json.load(respuesta)
        return datos


def tareas_urfd(raiz: Path) -> list[tuple[str, Path]]:
    tareas = [
        (f"{URFD}/fall-{i:02d}-cam0.mp4", raiz / f"fall-{i:02d}-cam0.mp4") for i in range(1, 31)
    ]
    tareas += [
        (f"{URFD}/adl-{i:02d}-cam0.mp4", raiz / f"adl-{i:02d}-cam0.mp4") for i in range(1, 41)
    ]
    tareas += [
        (f"{URFD}/urfall-cam0-{t}.csv", raiz / f"urfall-cam0-{t}.csv") for t in ("falls", "adls")
    ]
    return tareas


def tareas_caucafall(raiz: Path) -> list[tuple[str, Path]]:
    carpetas = leer_json(f"{MENDELEY}/folders/{VERSION_CAUCAFALL}")
    por_id = {str(c["id"]): c for c in carpetas}
    tareas = []
    for carpeta in carpetas:
        padre = por_id.get(str(carpeta.get("parent_id")))
        if padre is None or not str(padre["name"]).startswith("Subject"):
            continue  # only the activity folders inside each subject
        archivos = leer_json(
            f"{MENDELEY}/files?folder_id={carpeta['id']}&version={VERSION_CAUCAFALL}"
        )
        for archivo in archivos:
            if str(archivo["filename"]).lower().endswith(".avi"):
                url = str(archivo["content_details"]["download_url"])  # type: ignore[index]
                tareas.append((url, raiz / str(padre["name"]) / f"{carpeta['name']}.avi"))
    return tareas


def preparar_gmdcsa24(raiz: Path) -> None:
    """Downloads the GMDCSA24 zip, checks its MD5 and extracts it into ``raiz/v2.1``."""
    zip_ = raiz / "gmdcsa24-v2.1.zip"
    destino = raiz / "v2.1"
    if (destino / "Subject 4" / "ADL.csv").exists():
        print(f"ya existe {destino}")
        return
    print(bajar(ZENODO_GMDCSA24, zip_))
    md5 = hashlib.md5(usedforsecurity=False)
    with zip_.open("rb") as archivo:
        while bloque := archivo.read(1 << 20):
            md5.update(bloque)
    if md5.hexdigest() != MD5_GMDCSA24:
        raise OSError(f"MD5 de {zip_} no coincide: {md5.hexdigest()}")
    with zipfile.ZipFile(zip_) as comprimido:
        for miembro in comprimido.infolist():
            partes = Path(miembro.filename).parts[1:]  # drop the top folder of the zip
            if miembro.is_dir() or not partes or ".." in partes:
                continue
            if not miembro.filename.endswith(EXTRAER_GMDCSA24):
                continue
            salida = destino.joinpath(*partes)
            salida.parent.mkdir(parents=True, exist_ok=True)
            with comprimido.open(miembro) as origen, salida.open("wb") as archivo:
                shutil.copyfileobj(origen, archivo, 1 << 20)
    print(f"extraído {destino}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destino", type=Path, default=Path("datos"))
    parser.add_argument(
        "--datasets",
        nargs="+",
        choices=["urfd", "caucafall", "gmdcsa24"],
        default=["urfd", "caucafall"],
        help="gmdcsa24 is the hold-out test (1.1 GB); it is not downloaded by default",
    )
    args = parser.parse_args()

    if "gmdcsa24" in args.datasets:
        preparar_gmdcsa24(args.destino / "gmdcsa24")
    tareas = tareas_urfd(args.destino / "urfd") if "urfd" in args.datasets else []
    if "caucafall" in args.datasets:
        tareas += tareas_caucafall(args.destino / "caucafall")
    print(f"{len(tareas)} archivos por revisar…")
    errores = 0
    with ThreadPoolExecutor(max_workers=6) as grupo:
        futuros = [grupo.submit(bajar, url, destino) for url, destino in tareas]
        for futuro, (url, _) in zip(futuros, tareas, strict=True):
            try:
                futuro.result()
            except OSError as error:
                errores += 1
                print(f"ERROR {url}: {error}", file=sys.stderr)
    print(f"Listo: {len(tareas) - errores} archivos, {errores} errores.")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
