"""Configuración global leída de variables de entorno con prefijo ``TT_`` (ver ``.env.example``)."""

from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from detection_worker.clasificacion.umbrales import Umbrales


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TT_",
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    entorno: Literal["local", "produccion"] = "local"
    nivel_log: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Token que presenta el Agente de captura al abrir el WebSocket de ingesta.
    ingesta_token: SecretStr

    # Backend API del sistema (Spring Boot).
    backend_url: str
    backend_token: SecretStr

    # Estimación de pose.
    modelo_pose_ruta: Path = Path("models/pose_landmarker_lite.task")

    # Almacenamiento de clips (Amazon S3; en local, SeaweedFS con ``s3_endpoint_url``).
    clips_bucket: str
    aws_region: str = "us-east-1"
    s3_endpoint_url: str | None = None

    clasificacion: Umbrales
