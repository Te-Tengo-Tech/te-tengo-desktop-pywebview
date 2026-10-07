"""Global settings read from ``TT_``-prefixed environment variables (see ``.env.example``)."""

from pathlib import Path
from typing import Literal

from pydantic import SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from te_tengo_deteccion.clasificacion.umbrales import Umbrales


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TT_",
        env_file=".env",
        env_nested_delimiter="__",
        env_ignore_empty=True,  # an empty variable in .env counts as "not defined"
        extra="ignore",
    )

    entorno: Literal["local", "produccion"] = "local"
    nivel_log: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Token the Capture Agent presents when opening the ingestion WebSocket.
    ingesta_token: SecretStr

    # The system's Backend API (Spring Boot).
    backend_url: str
    backend_token: SecretStr

    # Pose estimation.
    modelo_pose_ruta: Path = Path("models/pose_landmarker_lite.task")

    # Clip storage (Amazon S3; locally, SeaweedFS with ``s3_endpoint_url``).
    clips_bucket: str
    aws_region: str = "us-east-1"
    s3_endpoint_url: str | None = None

    clasificacion: Umbrales = Umbrales()


class ConfiguracionInvalidaError(RuntimeError):
    """The environment configuration is incomplete or has invalid values."""


def cargar_settings() -> Settings:
    """Reads the configuration and, if it fails, explains which variable to check."""
    try:
        return Settings()  # the values come from the environment
    except ValidationError as error:
        problemas = []
        for detalle in error.errors():
            ruta = "__".join(str(parte) for parte in detalle["loc"]).upper()
            problemas.append(f"  - TT_{ruta}: {detalle['msg']}")
        raise ConfiguracionInvalidaError(
            "Configuración incompleta. Revisa tu .env (puedes generarlo con `make env`):\n"
            + "\n".join(problemas)
        ) from None
