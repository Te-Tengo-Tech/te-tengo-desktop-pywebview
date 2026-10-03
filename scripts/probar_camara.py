"""Prueba local del clasificador con la webcam o con un video, sin backend ni agente.

Usa el mismo código del worker (MediaPipe + parámetros + máquina de estados) y dibuja en
pantalla el esqueleto, la línea central, el rectángulo del cuerpo y los valores medidos.

Ejemplos:
    # Webcam: solo mide (sin umbral de velocidad no se clasifica)
    uv run python scripts/probar_camara.py

    # Webcam clasificando con un umbral PROVISIONAL elegido para experimentar
    uv run python scripts/probar_camara.py --velocidad-min 0.01

    # Video de URFD (la mitad derecha es RGB) guardando las mediciones para calibrar
    uv run python scripts/probar_camara.py --video fall-01-cam0.mp4 --recorte 320,0,320,240 \
        --csv mediciones.csv --sin-ventana

Teclas: q para salir.
"""

import argparse
import csv
import sys
import time
from pathlib import Path
from typing import Any

import cv2

from detection_worker.clasificacion.estados import ClasificadorCinematico, Evento
from detection_worker.clasificacion.medicion import Medicion, MedidorCinematico
from detection_worker.clasificacion.parametros import (
    extremos_linea_central,
    puntos_clave_visibles,
)
from detection_worker.clasificacion.umbrales import Umbrales
from detection_worker.pose.schemas import Pose
from detection_worker.pose.service import crear_landmarker, detectar

VERDE, ROJO, AMARILLO, BLANCO, CIAN = (
    (80, 200, 80),
    (60, 60, 230),
    (0, 210, 255),
    (255, 255, 255),
    (230, 200, 0),
)
ALTO_MAX = 480  # el agente envía 480p


def argumentos() -> argparse.Namespace:
    a = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    fuente = a.add_mutually_exclusive_group()
    fuente.add_argument("--camara", type=int, default=0, help="Índice de la webcam (por defecto 0)")
    fuente.add_argument("--video", type=Path, help="Archivo de video en lugar de la webcam")
    a.add_argument(
        "--fps",
        type=float,
        default=8.0,
        help="Fotogramas por segundo a analizar (5-10 como el agente)",
    )
    a.add_argument("--recorte", help="Región x,y,ancho,alto a usar (URFD: 320,0,320,240)")
    a.add_argument(
        "--velocidad-min", type=float, help="Umbral de velocidad PROVISIONAL para clasificar"
    )
    a.add_argument("--modelo", type=Path, default=Path("models/pose_landmarker_lite.task"))
    a.add_argument("--csv", type=Path, help="Guarda las mediciones de cada fotograma en un CSV")
    a.add_argument("--sin-ventana", action="store_true", help="No abre ventana; solo imprime")
    a.add_argument(
        "--listar-camaras", action="store_true", help="Muestra qué índice tiene cada cámara y sale"
    )
    return a.parse_args()


def preparar(imagen: Any, recorte: tuple[int, int, int, int] | None) -> Any:
    if recorte:
        x, y, w, h = recorte
        imagen = imagen[y : y + h, x : x + w]
    alto, ancho = imagen.shape[:2]
    if alto > ALTO_MAX:
        imagen = cv2.resize(imagen, (round(ancho * ALTO_MAX / alto / 2) * 2, ALTO_MAX))
    return imagen


def dibujar(
    imagen: Any,
    pose: Pose | None,
    medicion: Medicion | None,
    u: Umbrales,
    fase: str,
    eventos: list[str],
) -> None:
    if pose is not None:
        visibles = [
            pose.en_pixeles(i)
            for i, lm in enumerate(pose.landmarks)
            if lm.visibilidad >= u.visibilidad_min
        ]
        for p in visibles:
            cv2.circle(imagen, (int(p.x), int(p.y)), 3, VERDE, -1)
        if visibles:
            x0, x1 = min(p.x for p in visibles), max(p.x for p in visibles)
            y0, y1 = min(p.y for p in visibles), max(p.y for p in visibles)
            cv2.rectangle(imagen, (int(x0), int(y0)), (int(x1), int(y1)), AMARILLO, 1)
        cabeza, pies = extremos_linea_central(pose)
        cv2.line(imagen, (int(cabeza.x), int(cabeza.y)), (int(pies.x), int(pies.y)), CIAN, 2)

    lineas: list[tuple[str, tuple[int, int, int]]] = []
    if medicion is None:
        lineas.append(("sin persona visible", ROJO))
    else:
        prm, v = medicion.parametros, medicion.velocidad
        m2 = prm.angulo_grados < u.angulo_linea_central_max_grados
        m3 = prm.razon_ancho_alto >= u.razon_ancho_alto_min
        m1 = (
            None
            if (v is None or u.velocidad_descenso_min is None)
            else v >= u.velocidad_descenso_min
        )
        texto_v = "  -  " if v is None else f"{v:5.2f}"
        texto_m1 = "?" if m1 is None else ("SI" if m1 else "no")
        lineas += [
            (
                f"angulo   {prm.angulo_grados:5.1f} deg  M2={'SI' if m2 else 'no'}",
                ROJO if m2 else BLANCO,
            ),
            (
                f"razon    {prm.razon_ancho_alto:5.2f}      M3={'SI' if m3 else 'no'}",
                ROJO if m3 else BLANCO,
            ),
            (
                f"velocid. {texto_v} c/s  M1={texto_m1}",
                ROJO if m1 else BLANCO,
            ),
        ]
    if pose is not None and not puntos_clave_visibles(pose, u.visibilidad_min):
        lineas.append(("puntos clave poco visibles", AMARILLO))
    lineas.append((f"fase: {fase}", AMARILLO))
    lineas += [(e, ROJO) for e in eventos[-3:]]
    for i, (texto, color) in enumerate(lineas):
        cv2.putText(imagen, texto, (8, 20 + 18 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3)
        cv2.putText(imagen, texto, (8, 20 + 18 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)


def leer_recorte(texto: str | None) -> tuple[int, int, int, int] | None:
    """Convierte «x,y,ancho,alto» en una tupla."""
    if not texto:
        return None
    x, y, ancho, alto = (int(n) for n in texto.split(","))
    return x, y, ancho, alto


def listar_camaras(maximo: int = 6) -> None:
    """Guarda una foto de cada cámara para reconocerla, porque OpenCV no da sus nombres."""
    carpeta = Path("resultados/camaras")
    carpeta.mkdir(parents=True, exist_ok=True)
    for indice in range(maximo):
        captura = cv2.VideoCapture(indice)
        if not captura.isOpened():
            captura.release()
            break  # no hay más cámaras
        imagen = None
        for _ in range(15):  # las primeras lecturas pueden venir vacías mientras la cámara arranca
            ok, imagen = captura.read()
            if ok and imagen is not None and imagen.any():
                break
        captura.release()
        if imagen is None or not imagen.any():
            print(f"  --camara {indice}: no entrega imagen (¿cámara virtual sin usar?)")
            continue
        foto = carpeta / f"camara-{indice}.jpg"
        cv2.imwrite(str(foto), imagen)
        alto, ancho = imagen.shape[:2]
        print(f"  --camara {indice}: {ancho} × {alto} · foto: {foto}")


def main() -> int:
    args = argumentos()
    if args.listar_camaras:
        print("Cámaras disponibles. Abre las fotos para saber cuál es cuál:")
        listar_camaras()
        return 0
    if not args.modelo.is_file():
        print(f"Falta el modelo {args.modelo}. Ejecuta: make modelo", file=sys.stderr)
        return 1
    recorte = leer_recorte(args.recorte)
    umbrales = Umbrales(velocidad_descenso_min=args.velocidad_min)
    clasificador = ClasificadorCinematico(umbrales) if umbrales.calibrado else None
    medidor = MedidorCinematico(
        umbrales.intervalo_velocidad_s, umbrales.ventana_velocidad_s, umbrales.visibilidad_min
    )
    if clasificador is None:
        print("Sin --velocidad-min: solo se miden los parámetros (no se clasifican eventos).")
    else:
        print(f"Clasificando con velocidad mínima PROVISIONAL = {args.velocidad_min} cuerpos/s.")

    captura = cv2.VideoCapture(str(args.video) if args.video else args.camara)
    if not captura.isOpened():
        print(
            "No se pudo abrir la fuente de video. En macOS, da permiso de cámara a tu terminal.",
            file=sys.stderr,
        )
        return 1
    fps_fuente = captura.get(cv2.CAP_PROP_FPS) or 30.0
    landmarker = crear_landmarker(str(args.modelo), umbrales.visibilidad_min, modo="video")
    archivo_csv = args.csv.open("w", newline="", encoding="utf-8") if args.csv else None
    escritor = csv.writer(archivo_csv) if archivo_csv else None
    if escritor:
        escritor.writerow(
            ["instante_s", "angulo_grados", "razon_ancho_alto", "velocidad", "fase", "eventos"]
        )

    inicio, siguiente, indice = time.monotonic(), 0.0, 0
    eventos_vistos: list[str] = []
    try:
        while True:
            ok, imagen = captura.read()
            if not ok:
                break
            instante = indice / fps_fuente if args.video else time.monotonic() - inicio
            indice += 1
            if instante < siguiente:
                continue
            siguiente = instante + 1 / args.fps

            imagen = preparar(imagen, recorte)
            pose = detectar(landmarker, imagen, round(instante * 1000))
            eventos: list[Evento] = []
            if clasificador is not None:
                eventos = clasificador.actualizar(instante, pose)
                medicion = clasificador.ultima_medicion if pose is not None else None
                fase = clasificador.fase.value
            else:
                medicion = medidor.medir(instante, pose) if pose is not None else None
                fase = "(sin clasificar)"
            for e in eventos:
                texto = f"{e.instante:7.2f}s  EVENTO {e.tipo.value.upper()}"
                eventos_vistos.append(texto)
                print(texto, e.parametros)
            if escritor and medicion is not None:
                p = medicion.parametros
                escritor.writerow(
                    [
                        f"{instante:.3f}",
                        f"{p.angulo_grados:.2f}",
                        f"{p.razon_ancho_alto:.3f}",
                        "" if medicion.velocidad is None else f"{medicion.velocidad:.3f}",
                        fase,
                        " ".join(e.tipo.value for e in eventos),
                    ]
                )
            if not args.sin_ventana:
                dibujar(imagen, pose, medicion, umbrales, fase, eventos_vistos)
                cv2.imshow("Te Tengo - prueba del clasificador (q para salir)", imagen)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    finally:
        captura.release()
        landmarker.close()
        if archivo_csv:
            archivo_csv.close()
        if not args.sin_ventana:
            cv2.destroyAllWindows()
    print(f"Fin. Eventos detectados: {len(eventos_vistos)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
