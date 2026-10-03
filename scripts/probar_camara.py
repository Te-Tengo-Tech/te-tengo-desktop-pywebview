"""Prueba local del clasificador con la webcam o con un video, sin backend ni agente.

Usa el mismo código del worker (MediaPipe + parámetros + máquina de estados) y dibuja en
pantalla el esqueleto, la línea central, el rectángulo del cuerpo y los valores medidos.

Ejemplos:
    # Webcam con el umbral calibrado (0,01 cuerpos/s)
    uv run python scripts/probar_camara.py --camara 0

    # Solo medir, sin clasificar
    uv run python scripts/probar_camara.py --solo-medir

    # Video de URFD (la mitad derecha es RGB) guardando las mediciones
    uv run python scripts/probar_camara.py --video fall-01-cam0.mp4 --recorte 320,0,320,240 \
        --csv mediciones.csv --sin-ventana

Teclas: q salir · r reiniciar el clasificador · c guardar una captura en resultados/capturas/.
"""

import argparse
import csv
import sys
import time
from pathlib import Path
from typing import Any

import cv2
from visor import Estado, Visor

from detection_worker.clasificacion.estados import ClasificadorCinematico, Evento
from detection_worker.clasificacion.medicion import MedidorCinematico
from detection_worker.clasificacion.umbrales import Umbrales
from detection_worker.pose.service import crear_landmarker, detectar

ALTO_MAX = 480  # el agente envía 480p
VELOCIDAD_CALIBRADA = 0.01  # docs/validacion.md


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
        "--velocidad-min",
        type=float,
        default=VELOCIDAD_CALIBRADA,
        help=f"Umbral de velocidad (por defecto el calibrado, {VELOCIDAD_CALIBRADA})",
    )
    a.add_argument("--solo-medir", action="store_true", help="Mide sin clasificar eventos")
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
    umbrales = Umbrales(velocidad_descenso_min=None if args.solo_medir else args.velocidad_min)
    clasificador = ClasificadorCinematico(umbrales) if umbrales.calibrado else None
    medidor = MedidorCinematico(
        umbrales.intervalo_velocidad_s, umbrales.ventana_velocidad_s, umbrales.visibilidad_min
    )
    if clasificador is None:
        print("Modo solo medición: se muestran los parámetros, pero no se clasifican eventos.")
    else:
        print(f"Clasificando con velocidad mínima = {umbrales.velocidad_descenso_min} cuerpos/s.")

    captura = cv2.VideoCapture(str(args.video) if args.video else args.camara)
    if not captura.isOpened():
        print(
            "No se pudo abrir la fuente de video. En macOS, da permiso de cámara a tu terminal.",
            file=sys.stderr,
        )
        return 1
    fps_fuente = captura.get(cv2.CAP_PROP_FPS) or 30.0
    nombre_fuente = args.video.name if args.video else f"Cámara {args.camara}"
    landmarker = crear_landmarker(str(args.modelo), umbrales.visibilidad_min, modo="video")
    visor = Visor(umbrales)
    archivo_csv = args.csv.open("w", newline="", encoding="utf-8") if args.csv else None
    escritor = csv.writer(archivo_csv) if archivo_csv else None
    if escritor:
        escritor.writerow(
            ["instante_s", "angulo_grados", "razon_ancho_alto", "velocidad", "fase", "eventos"]
        )

    inicio, siguiente, indice = time.monotonic(), 0.0, 0
    fps_medido, ultimo = 0.0, None
    eventos_vistos: list[tuple[float, str]] = []
    titulo = "Te Tengo - prueba del clasificador"
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
            if ultimo is not None and instante > ultimo:
                fps_medido = (
                    0.8 * fps_medido + 0.2 / (instante - ultimo)
                    if fps_medido
                    else 1 / (instante - ultimo)
                )
            ultimo = instante

            imagen = preparar(imagen, recorte)
            pose = detectar(landmarker, imagen, round(instante * 1000))
            eventos: list[Evento] = []
            if clasificador is not None:
                eventos = clasificador.actualizar(instante, pose)
                medicion = clasificador.ultima_medicion if pose is not None else None
                fase, tiempos = clasificador.fase, clasificador.tiempos(instante)
            else:
                medicion = medidor.medir(instante, pose) if pose is not None else None
                fase, tiempos = None, None
            for e in eventos:
                eventos_vistos.append((e.instante, e.tipo.value))
                print(f"{e.instante:7.2f} s  {e.tipo.value}  {e.parametros}")
            if escritor and medicion is not None:
                p = medicion.parametros
                escritor.writerow(
                    [
                        f"{instante:.3f}",
                        f"{p.angulo_grados:.2f}",
                        f"{p.razon_ancho_alto:.3f}",
                        "" if medicion.velocidad is None else f"{medicion.velocidad:.3f}",
                        "" if fase is None else fase.value,
                        " ".join(e.tipo.value for e in eventos),
                    ]
                )
            if args.sin_ventana:
                continue
            estado = Estado(
                pose, medicion, fase, tiempos, instante, fps_medido, nombre_fuente, eventos_vistos
            )
            cuadro = visor.componer(imagen, estado)
            cv2.imshow(titulo, cuadro)
            tecla = cv2.waitKey(1) & 0xFF
            if tecla == ord("q"):
                break
            if tecla == ord("r") and clasificador is not None:
                clasificador = ClasificadorCinematico(umbrales)
                eventos_vistos.clear()
                print("Clasificador reiniciado.")
            if tecla == ord("c"):
                carpeta = Path("resultados/capturas")
                carpeta.mkdir(parents=True, exist_ok=True)
                destino = carpeta / f"captura-{time.strftime('%Y%m%d-%H%M%S')}.png"
                cv2.imwrite(str(destino), cuadro)
                print(f"Captura guardada en {destino}")
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
