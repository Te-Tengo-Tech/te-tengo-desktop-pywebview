"""Entry point: ``uv run te-tengo-captura``."""

import argparse
import logging
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from te_tengo_captura import (
    __version__,
    autoinicio,
    config,
    registro,
    restablecer,
    rutas,
    sin_interfaz,
)
from te_tengo_captura.agente import Agente
from te_tengo_captura.agente_pc import FabricaCamaras
from te_tengo_captura.backend.cliente import ClienteBackend
from te_tengo_captura.backend.falso import URL_API, BackendFalso
from te_tengo_captura.captura.dispositivos import FuenteWebcamPorId
from te_tengo_captura.captura.fuentes import FuenteArchivo, FuenteVideo, FuenteWebcam
from te_tengo_captura.captura.pose import EstimadorMediaPipe, ruta_modelo_predeterminada
from te_tengo_captura.coordinador import Coordinador
from te_tengo_captura.diario import Diario, ManejadorDiario
from te_tengo_captura.instancia import Instancia
from te_tengo_captura.vinculacion.credenciales import (
    AlmacenCredenciales,
    Llavero,
    LlaveroEnMemoria,
)

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
        "--restablecer",
        action="store_true",
        help=(
            "unlink this PC (if online), delete its credentials, configuration, data and logs "
            "and the start with the system, then exit (the Windows uninstaller runs it)"
        ),
    )
    parser.add_argument(
        "--motivo",
        choices=restablecer.MOTIVOS,
        default="restablecida",
        help="with --restablecer: what the family's activity log says (default: restablecida)",
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
    args: argparse.Namespace,
    configuracion: config.Configuracion | config.AjustesPc,
    diario: Diario | None = None,
) -> Coordinador:
    """The installation, or a PC that links with a code (US-28) when there is no credential."""
    modelo = args.modelo or ruta_modelo_predeterminada()
    if not modelo.is_file():  # fail at once, as before, instead of when a camera starts
        raise FileNotFoundError(f"No existe el modelo {modelo}. Descárgalo con: make modelo")
    falso = BackendFalso(credencial="", aprobar_tras=3) if args.backend_falso else None
    fabrica: Callable[[Callable[[str], None]], Agente] | None = None
    olvidar: Callable[[], None] = _nada
    ruta_config = args.config or config.ruta_predeterminada()

    def olvidar_configuracion() -> None:
        if falso is None:  # a demo never deletes the example file
            restablecer.borrar_configuracion(ruta_config)

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

    def crear_estimador() -> EstimadorMediaPipe:
        # One landmarker per camera: VIDEO mode keeps per-stream tracking state (ADR 0006).
        return EstimadorMediaPipe(modelo)

    ajustes = configuracion if isinstance(configuracion, config.AjustesPc) else config.AjustesPc()
    video = args.video

    def abrir_fuente(dispositivo_id: str) -> FuenteVideo:
        if video is not None:  # demos and end-to-end tests: every camera in use plays the file
            return FuenteArchivo(video, repetir=True, tiempo_real=True)
        return FuenteWebcamPorId(dispositivo_id)

    camaras = FabricaCamaras(
        ajustes=ajustes,
        crear_estimador=crear_estimador,
        abrir_fuente=abrir_fuente,
        transporte=falso.transporte() if falso is not None else None,
        canal=falso is None,
    )
    # The demo never touches the OS credential store.
    llavero: Llavero | None = LlaveroEnMemoria() if falso is not None else None
    return Coordinador(
        __version__,
        URL_API if falso is not None else api_url,
        args.datos or rutas.datos(),
        # The demo never touches the OS credential store.
        AlmacenCredenciales(llavero),
        instalacion=fabrica,
        olvidar_instalacion=olvidar,
        olvidar_configuracion=olvidar_configuracion,
        transporte=falso.transporte() if falso is not None else None,
        canal_pc=falso is None,
        fabrica=camaras,
        diario=diario,
        registros=args.logs or rutas.logs(),
        llavero=llavero,
        carpeta_datos=(args.datos or rutas.datos()) / "Datos",
    )


def ejecutar_aplicacion(
    agente: Coordinador, instancia_abrir: dict[str, Callable[[], None]]
) -> None:
    from te_tengo_captura.ui.aplicacion import Aplicacion

    aplicacion = Aplicacion(agente)
    instancia_abrir["abrir"] = aplicacion.abrir
    aplicacion.ejecutar()


def ejecutar_restablecer(args: argparse.Namespace) -> int:
    """``--restablecer``: before any log file is opened, so the logs can be deleted too."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    datos = args.datos or rutas.datos()
    instancia = Instancia(datos)
    if not instancia.adquirir(lambda: None):
        print(
            "Te Tengo Captura está abierto: elige «Salir» y vuelve a intentarlo.", file=sys.stderr
        )
        return 3
    instancia.liberar()
    ruta_config = args.config or config.ruta_predeterminada()
    try:
        cargada = config.cargar(args.config)
        api_url = args.api_url or cargada.api_url
    except (config.ConfiguracionInvalidaError, FileNotFoundError):
        api_url = args.api_url or config.AjustesPc().api_url
    resultado = restablecer.ejecutar(
        api_url,
        AlmacenCredenciales(),
        datos,
        ruta_config,
        args.logs or rutas.logs(),
        args.motivo,
    )
    if resultado.vinculada and not resultado.avisada:
        print(
            "Sin conexión: la PC seguirá en la app como «Sin conexión» hasta que la quites.",
            file=sys.stderr,
        )
    print("Te Tengo Captura se restableció en esta PC.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = argumentos(argv)
    if args.restablecer:
        return ejecutar_restablecer(args)
    secretos: list[Callable[[], list[str]]] = []
    ruta_log = registro.configurar(
        args.logs or rutas.logs(), lambda: [s for fuente in secretos for s in fuente()]
    )
    # The advanced mode's live log (US-32): a handler that keeps the cameras' lines in memory.
    diario = Diario()
    logging.getLogger().addHandler(ManejadorDiario(diario))
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
        agente = construir(args, configuracion, diario)
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
