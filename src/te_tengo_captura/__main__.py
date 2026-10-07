"""Entry point: ``uv run te-tengo-captura``."""

import argparse
import logging
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from te_tengo_captura import __version__, autoinicio, config, registro, rutas
from te_tengo_captura.agente import Agente
from te_tengo_captura.backend.cliente import ClienteBackend
from te_tengo_captura.backend.falso import URL_API, BackendFalso
from te_tengo_captura.captura.fuentes import FuenteArchivo, FuenteVideo, FuenteWebcam
from te_tengo_captura.captura.pose import EstimadorMediaPipe, ruta_modelo_predeterminada
from te_tengo_captura.instancia import Instancia

logger = logging.getLogger(__name__)


def argumentos(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="te-tengo-captura", description="Te Tengo Captura")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--config",
        type=Path,
        help=f"installation file (default: {config.ruta_predeterminada()})",
    )
    parser.add_argument(
        "--backend-falso",
        action="store_true",
        help="use the in-memory backend instead of the API (local runs and demos)",
    )
    parser.add_argument(
        "--video", type=Path, help="play a video file in a loop instead of the webcam (demos)"
    )
    parser.add_argument("--modelo", type=Path, help="MediaPipe pose model (.task)")
    parser.add_argument("--datos", type=Path, help="data directory (outbox and pending clips)")
    parser.add_argument("--logs", type=Path, help="log directory")
    parser.add_argument(
        "--autoprueba",
        action="store_true",
        help="check the model, clip encoding and UI libraries, then exit (packaging smoke test)",
    )
    return parser.parse_args(argv)


def construir_agente(args: argparse.Namespace, configuracion: config.Configuracion) -> Agente:
    credencial = configuracion.credencial_instalacion.get_secret_value()
    if args.backend_falso:
        falso = BackendFalso(credencial=credencial)
        cliente = ClienteBackend(
            URL_API,
            credencial,
            configuracion.camara.nombre_habitacion,
            __version__,
            transporte=falso.transporte(),
        )
    else:
        cliente = ClienteBackend(
            configuracion.api_url, credencial, configuracion.camara.nombre_habitacion, __version__
        )
    fuente: FuenteVideo = (
        FuenteArchivo(args.video, repetir=True, tiempo_real=True)
        if args.video
        else FuenteWebcam(configuracion.webcam.indice)
    )
    estimador = EstimadorMediaPipe(
        args.modelo or ruta_modelo_predeterminada(), configuracion.clasificacion.visibilidad_min
    )
    return Agente(
        configuracion,
        cliente,
        fuente,
        estimador,
        args.datos or rutas.datos(),
        __version__,
    )


def ejecutar_aplicacion(agente: Agente, instancia_abrir: dict[str, Callable[[], None]]) -> None:
    from te_tengo_captura.ui.aplicacion import Aplicacion

    aplicacion = Aplicacion(agente)
    instancia_abrir["abrir"] = aplicacion.abrir
    aplicacion.ejecutar()


def main(argv: Sequence[str] | None = None) -> int:
    args = argumentos(argv)
    secretos: list[Callable[[], list[str]]] = []
    ruta_log = registro.configurar(
        args.logs or rutas.logs(), lambda: [s for fuente in secretos for s in fuente()]
    )
    logger.info("Te Tengo Captura %s; registro en %s", __version__, ruta_log)
    if args.autoprueba:
        from te_tengo_captura import autoprueba

        return autoprueba.ejecutar(args.modelo or ruta_modelo_predeterminada())
    # A second launch shows the running agent's window instead of starting another agent.
    instancia = Instancia(args.datos or rutas.datos())
    abrir: dict[str, Callable[[], None]] = {}
    if not instancia.adquirir(lambda: abrir.get("abrir", lambda: None)()):
        instancia.avisar()
        return 0
    try:
        configuracion = config.cargar(args.config)
        secretos.append(lambda: [configuracion.credencial_instalacion.get_secret_value()])
        agente = construir_agente(args, configuracion)
        secretos.append(agente.secretos)
    except (config.ConfiguracionInvalidaError, FileNotFoundError) as error:
        logger.error("%s", error)
        print(error, file=sys.stderr)
        instancia.liberar()
        return 2
    autoinicio.registrar()
    try:
        ejecutar_aplicacion(agente, abrir)
    finally:
        instancia.liberar()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
