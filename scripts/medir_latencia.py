"""Per-frame latency and throughput of the detection pipeline on this machine.

It runs videos one after another in a single process, with the same steps as
``evaluar.fotogramas_validacion`` and the agent (sampling by time at ``--fps``, 480p, JPEG
quality 80 round trip, MediaPipe Pose Landmarker lite in VIDEO mode on the CPU delegate, then
the ``ClasificadorCinematico`` with the shipped thresholds), and times each stage of every
sampled frame with ``time.perf_counter``:

* ``decodificar``: reading source frames until the next sampled one (file decoding; a webcam
  delivers frames instead, so this stage is not part of the agent's cost per frame);
* ``preprocesar``: resize to 480p and JPEG encode + decode;
* ``mediapipe``: BGR→RGB, ``mp.Image`` and ``detect_for_video`` (the first frame of each video,
  which includes graph warm-up, is reported apart);
* ``clasificar``: ``ClasificadorCinematico.actualizar``.

It also reports the wall-clock throughput (sampled frames per second) and the real-time factor
(seconds of video processed per second), plus the hardware and library versions.

Example:
    uv run python scripts/medir_latencia.py --datasets gmdcsa24 --salida resultados/latencia.md
"""

import argparse
import math
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

from evaluar import ALTO_MAX, CALIDAD_JPEG, DATASETS_VALIDACION, RESULTADOS, listar_videos

from te_tengo_deteccion.clasificacion.estados import ClasificadorCinematico
from te_tengo_deteccion.clasificacion.umbrales import Umbrales
from te_tengo_deteccion.pose.service import crear_landmarker, detectar

ETAPAS = ("decodificar", "preprocesar", "mediapipe", "clasificar")


def percentil(xs: list[float], q: float) -> float:
    ordenadas = sorted(xs)
    return ordenadas[min(len(ordenadas) - 1, max(0, math.ceil(q * len(ordenadas)) - 1))]


def cpu() -> str:
    if sys.platform == "darwin":
        r = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True
        )
        return r.stdout.strip() or platform.processor()
    return platform.processor() or platform.machine()


def main() -> int:
    import cv2
    import mediapipe as mp

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--fps", type=float, default=8.0)
    parser.add_argument("--modelo", type=Path, default=Path("models/pose_landmarker_lite.task"))
    parser.add_argument("--datos", type=Path, default=Path("datos"))
    parser.add_argument(
        "--datasets",
        nargs="+",
        choices=[*DATASETS_VALIDACION, "gmdcsa24"],  # video files only
        default=["gmdcsa24"],
    )
    parser.add_argument("--max-videos", type=int, default=0, help="0 = all")
    parser.add_argument("--salida", type=Path, default=RESULTADOS / "latencia.md")
    args = parser.parse_args()

    videos = listar_videos(args.datos, args.datasets)
    if args.max_videos:
        videos = videos[: args.max_videos]
    if not videos:
        print("No hay videos.", file=sys.stderr)
        return 1
    tiempos: dict[str, list[float]] = {e: [] for e in ETAPAS}
    primeros: list[float] = []
    agente: list[float] = []  # preprocess + MediaPipe + classifier, warm-up frames excluded
    segundos_video = 0.0
    muestras = 0
    inicio_total = time.perf_counter()
    for video in videos:
        landmarker = crear_landmarker(str(args.modelo), modo="video")
        clasificador = ClasificadorCinematico(Umbrales(velocidad_descenso_min=0.01))
        captura = cv2.VideoCapture(str(video.ruta))
        fps_fuente = captura.get(cv2.CAP_PROP_FPS) or 30.0
        siguiente, indice, primero = 0.0, 0, True
        t0 = time.perf_counter()
        try:
            while True:
                ok, imagen = captura.read()
                if not ok:
                    break
                instante = indice / fps_fuente
                indice += 1
                if instante + 1e-9 < siguiente:
                    continue
                siguiente += 1 / args.fps
                t1 = time.perf_counter()
                if video.recorte:
                    x, y, w, h = video.recorte
                    imagen = imagen[y : y + h, x : x + w]
                alto, ancho = imagen.shape[:2]
                if alto > ALTO_MAX:
                    imagen = cv2.resize(imagen, (round(ancho * ALTO_MAX / alto / 2) * 2, ALTO_MAX))
                _, comprimida = cv2.imencode(
                    ".jpg", imagen, [cv2.IMWRITE_JPEG_QUALITY, CALIDAD_JPEG]
                )
                imagen = cv2.imdecode(comprimida, cv2.IMREAD_COLOR)  # type: ignore[assignment]
                t2 = time.perf_counter()
                pose = detectar(landmarker, imagen, round(instante * 1000))
                t3 = time.perf_counter()
                clasificador.actualizar(instante, pose)
                t4 = time.perf_counter()
                tiempos["decodificar"].append(t1 - t0)
                tiempos["preprocesar"].append(t2 - t1)
                (primeros if primero else tiempos["mediapipe"]).append(t3 - t2)
                if not primero:
                    agente.append((t4 - t1) * 1000)
                tiempos["clasificar"].append(t4 - t3)
                primero = False
                muestras += 1
                t0 = time.perf_counter()
            segundos_video += indice / fps_fuente
        finally:
            captura.release()
            landmarker.close()
    total = time.perf_counter() - inicio_total

    lineas = [
        "# Detection pipeline latency on this machine",
        "",
        f"- CPU: {cpu()} ({os.cpu_count()} logical cores); OS: {platform.platform()}",
        f"- Python {platform.python_version()}; MediaPipe {mp.__version__}; OpenCV "
        f"{cv2.__version__}; model `{args.modelo.name}`, VIDEO mode, CPU delegate (XNNPACK)",
        f"- Videos: {len(videos)} ({', '.join(args.datasets)}), {segundos_video:.0f} s of video, "
        f"{muestras} sampled frames at {args.fps:g} fps; one process, videos in sequence",
        "",
        "| Stage | Mean (ms) | Median (ms) | p95 (ms) | Max (ms) | Frames |",
        "|---|---|---|---|---|---|",
    ]
    for etapa in ETAPAS:
        xs = [x * 1000 for x in tiempos[etapa]]
        lineas.append(
            f"| {etapa} | {statistics.mean(xs):.2f} | {statistics.median(xs):.2f} | "
            f"{percentil(xs, 0.95):.2f} | {max(xs):.2f} | {len(xs)} |"
        )
    pm = [x * 1000 for x in primeros]
    lineas += [
        "",
        f"- First MediaPipe frame of each video (graph warm-up, excluded above): mean "
        f"{statistics.mean(pm):.1f} ms, max {max(pm):.1f} ms.",
        f"- Agent cost per frame (preprocess + MediaPipe + classifier): "
        f"mean {statistics.mean(agente):.2f} ms, p95 {percentil(agente, 0.95):.2f} ms: "
        f"{100 * statistics.mean(agente) / (1000 / args.fps):.1f} % of the "
        f"{1000 / args.fps:.0f} ms budget per frame at {args.fps:g} fps (MediaPipe may use "
        "several threads, so this is wall time, not single-core load).",
        f"- Wall-clock throughput including file decoding and landmarker creation: "
        f"{muestras / total:.1f} sampled frames/s; real-time factor {segundos_video / total:.1f}× "
        f"({total:.1f} s for {segundos_video:.0f} s of video).",
    ]
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("\n".join(lineas))
    return 0


if __name__ == "__main__":
    sys.exit(main())
