"""Punto de entrada: ``uvicorn detection_worker.main:create_app --factory``."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI

from detection_worker import __version__
from detection_worker.clips.service import AlmacenClips, S3AlmacenClips
from detection_worker.config import Settings, cargar_settings
from detection_worker.eventos.client import BackendPublicador, PublicadorEventos
from detection_worker.ingesta.router import router as ingesta_router
from detection_worker.pose.service import EstimadorPose, MediaPipeEstimador
from detection_worker.salud.router import router as salud_router

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Componentes:
    """Adaptadores externos. En las pruebas se reemplazan por dobles."""

    estimador: EstimadorPose
    publicador: PublicadorEventos
    almacen: AlmacenClips


def construir_componentes(settings: Settings) -> Componentes:
    return Componentes(
        estimador=MediaPipeEstimador(
            settings.modelo_pose_ruta, settings.clasificacion.visibilidad_min
        ),
        publicador=BackendPublicador(
            settings.backend_url, settings.backend_token.get_secret_value()
        ),
        almacen=S3AlmacenClips(
            settings.clips_bucket, settings.aws_region, settings.s3_endpoint_url
        ),
    )


def create_app(settings: Settings | None = None, componentes: Componentes | None = None) -> FastAPI:
    settings = settings or cargar_settings()
    logging.basicConfig(
        level=settings.nivel_log,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = settings
        if not settings.clasificacion.calibrado:
            logger.warning(
                "Servicio sin calibrar: falta TT_CLASIFICACION__VELOCIDAD_DESCENSO_MIN. "
                "/health funciona, pero la ingesta rechazará el video hasta definirlo."
            )
        app.state.componentes = componentes or construir_componentes(settings)
        try:
            yield
        finally:
            app.state.componentes.estimador.cerrar()
            await app.state.componentes.publicador.cerrar()

    app = FastAPI(
        title="Te Tengo · Módulo de detección",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs" if settings.entorno == "local" else None,
        redoc_url=None,
    )
    app.include_router(salud_router)
    app.include_router(ingesta_router)
    return app
