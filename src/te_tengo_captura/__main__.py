"""Entry point: ``uv run te-tengo-captura``."""

import argparse
import logging
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from te_tengo_captura import __version__, autoinicio, config, registro, rutas, sin_interfaz
from te_tengo_captura.agente import Agente
from te_tengo_captura.backend.cliente import ClienteBackend
from te_tengo_captura.backend.falso import URL_API, BackendFalso
from te_tengo_captura.captura.fuentes import FuenteArchivo, FuenteVideo, FuenteWebcam
from te_tengo_captura.captura.pose import EstimadorMediaPipe, ruta_modelo_predeterminada
from te_tengo_captura.coordinador import Coordinador
from te_tengo_captura.instancia import Instancia
from te_tengo_captura.vinculacion.credenciales import AlmacenCredenciales, LlaveroEnMemoria

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
        "--api-url", help="URL of te-tengo-general-api for a linked PC (default: production)"
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
        "--sin-interfaz",
        action="store_true",
        help="run without window or tray until Ctrl+C or SIGTERM (no display: end-to-end tests)",
    )
    parser.add_argument(
        "--marca-tiempo",
        action="store_true",
        help="draw the capture time in ms on the live view (debug: glass-to-glass latency)",
    )
    parser.add_argument(
        "--autoprueba",
        action="store_true",
        help="check the model, clip encoding and UI libraries, then exit (packaging smoke test)",
    )
    return parser.parse_args(argv)


def construir_agente(
    args: argparse.Namespace,
    configuracion: config.Configuracion,
    al_desvincular: Callable[[str], None] | None = None,
    falso: BackendFalso | None = None,
) -> Agente:
    """An installation's agent (the project team's ``config.toml``)."""
    if args.marca_tiempo:
        vista = configuracion.vista_en_vivo.model_copy(update={"marca_tiempo": True})
        configuracion = configuracion.model_copy(update={"vista_en_vivo": vista})
    credencial = configuracion.credencial_instalacion.get_secret_value()
    if falso is None and args.backend_falso:
        falso = BackendFalso(credencial=credencial)
    if falso is not None:
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
    # MediaPipe keeps the confidences of the validation (``crear_landmarker``'s default);
    # ``visibilidad_min`` is the classifier's A5 and must not change the pose detector.
    estimador = EstimadorMediaPipe(args.modelo or ruta_modelo_predeterminada())
    return Agente(
        configuracion,
        cliente,
        fuente,
        estimador,
        args.datos or rutas.datos(),
        __version__,
        vista_en_vivo=falso is None,
        al_desvincular=al_desvincular,
    )


def _nada() -> None:
    pass


def construir(
    args: argparse.Namespace, configuracion: config.Configuracion | config.AjustesPc
) -> Coordinador:
    """The installation, or a PC that links with a code (US-28) when there is no credential."""
    modelo = args.modelo or ruta_modelo_predeterminada()
    if not modelo.is_file():  # fail at once, as before, instead of when a camera starts
        raise FileNotFoundError(f"No existe el modelo {modelo}. Descárgalo con: make modelo")
    falso = BackendFalso(credencial="", aprobar_tras=3) if args.backend_falso else None
    fabrica: Callable[[Callable[[str], None]], Agente] | None = None
    olvidar: Callable[[], None] = _nada
    if isinstance(configuracion, config.Configuracion):
        instalacion = configuracion
        if falso is not None:
            falso.credencial = instalacion.credencial_instalacion.get_secret_value()
        ruta = args.config or config.ruta_predeterminada()

        def instalar(al_desvincular: Callable[[str], None]) -> Agente:
            return construir_agente(args, instalacion, al_desvincular, falso)

        def olvidar_credencial() -> None:
            if falso is None:  # a demo never edits the example file
                config.olvidar_credencial(ruta)

        fabrica, olvidar = instalar, olvidar_credencial
        api_url = instalacion.api_url
    else:
        api_url = args.api_url or configuracion.api_url
    return Coordinador(
        __version__,
        URL_API if falso is not None else api_url,
        args.datos or rutas.datos(),
        # The demo never touches the OS credential store.
        AlmacenCredenciales(LlaveroEnMemoria() if falso is not None else None),
        instalacion=fabrica,
        olvidar_instalacion=olvidar,
        transporte=falso.transporte() if falso is not None else None,
        canal_pc=falso is None,
    )


def ejecutar_aplicacion(
    agente: Coordinador, instancia_abrir: dict[str, Callable[[], None]]
) -> None:
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
        if isinstance(configuracion, config.Configuracion):
            credencial = configuracion.credencial_instalacion.get_secret_value()
            secretos.append(lambda: [credencial])
        agente = construir(args, configuracion)
        secretos.append(agente.secretos)
    except (config.ConfiguracionInvalidaError, FileNotFoundError) as error:
        logger.error("%s", error)
        print(error, file=sys.stderr)
        instancia.liberar()
        return 2
    try:
        if args.sin_interfaz:
            # Not the household install: no autostart entry, which would start it with a window.
            sin_interfaz.ejecutar(agente)
        else:
            autoinicio.registrar()
            ejecutar_aplicacion(agente, abrir)
    finally:
        instancia.liberar()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
