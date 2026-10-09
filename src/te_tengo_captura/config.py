"""Fixed installation configuration, written by the project team in a TOML file.

The file lives in the platform config directory (``platformdirs``, app name ``TeTengoCaptura``)
or is passed with ``--config <ruta>``. The agent has no settings screen: the family manages the
room name, pauses and consent in the mobile app. ``config.ejemplo.toml`` documents every field.
"""

import tomllib
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, field_validator

from te_tengo_deteccion.clasificacion.umbrales import Umbrales

NOMBRE_APP = "TeTengoCaptura"
NOMBRE_ARCHIVO = "config.toml"

# Calibrated values (docs/validation.md, section 4). Only the speed threshold (R1) has no default
# in the detection core; the other thresholds keep the defaults of ``Umbrales``.
UMBRALES_CALIBRADOS: dict[str, float] = {"velocidad_descenso_min": 0.01}


class _Seccion(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)


class Webcam(_Seccion):
    indice: int = Field(ge=0, description="Índice de la webcam para OpenCV (0 es la primera).")
    nombre: str = Field(min_length=1, description="Nombre que se muestra, p. ej. «Webcam USB HD».")
    especificacion: str = Field(min_length=1, description="Detalle, p. ej. «USB · 1920 × 1080».")


class Vivienda(_Seccion):
    nombre_adulto_mayor: str = Field(min_length=1)
    direccion: str = Field(min_length=1)


class Camara(_Seccion):
    nombre_habitacion: str = Field(min_length=1)


class VistaEnVivo(_Seccion):
    """Optional ``[vista_en_vivo]`` table (``docs/AGENT_CONTRACT.md``, "Live view")."""

    fps: float = Field(
        default=15.0, ge=1.0, le=30.0, description="Cuadros por segundo de la vista en vivo."
    )
    marca_tiempo: bool = Field(
        default=False, description="Dibuja la hora de captura en ms (solo para medir latencia)."
    )


class Configuracion(_Seccion):
    api_url: str = Field(min_length=1)
    credencial_instalacion: SecretStr
    instalada_el: date
    webcam: Webcam
    vivienda: Vivienda
    camara: Camara
    clasificacion: Umbrales = Umbrales(**UMBRALES_CALIBRADOS)
    vista_en_vivo: VistaEnVivo = VistaEnVivo()

    @field_validator("api_url")
    @classmethod
    def _url_http(cls, valor: str) -> str:
        if not valor.startswith(("http://", "https://")):
            raise ValueError("debe empezar con http:// o https://")
        return valor.rstrip("/")

    @field_validator("credencial_instalacion")
    @classmethod
    def _credencial_no_vacia(cls, valor: SecretStr) -> SecretStr:
        if not valor.get_secret_value().strip():
            raise ValueError("no puede estar vacía")
        return valor

    @field_validator("clasificacion", mode="before")
    @classmethod
    def _sobre_calibrados(cls, valor: Any) -> Any:
        # Overrides in [clasificacion] apply on top of the calibrated values, not on top of the
        # uncalibrated defaults of the core.
        if isinstance(valor, dict):
            return {**UMBRALES_CALIBRADOS, **valor}
        return valor


class ConfiguracionInvalidaError(RuntimeError):
    """The installation file is missing, unreadable or has missing or invalid fields."""


def ruta_predeterminada() -> Path:
    """``config.toml`` in the platform config directory (e.g. ``%APPDATA%\\TeTengoCaptura``)."""
    from platformdirs import user_config_path

    return user_config_path(NOMBRE_APP, appauthor=False, roaming=True) / NOMBRE_ARCHIVO


def cargar(ruta: Path | None = None) -> Configuracion:
    """Reads and validates the installation file; the error explains, in Spanish, what to fix."""
    ruta = ruta or ruta_predeterminada()
    try:
        datos = tomllib.loads(ruta.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfiguracionInvalidaError(
            f"No se encontró el archivo de configuración {ruta}. "
            "Avisa al equipo del proyecto para que lo instale."
        ) from None
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise ConfiguracionInvalidaError(
            f"No se pudo leer el archivo de configuración {ruta}: {error}"
        ) from None
    try:
        return Configuracion.model_validate(datos)
    except ValidationError as error:
        raise ConfiguracionInvalidaError(_explicar(ruta, error)) from None


def _explicar(ruta: Path, error: ValidationError) -> str:
    problemas = []
    for detalle in error.errors():
        campo = ".".join(str(parte) for parte in detalle["loc"])
        if detalle["type"] == "missing":
            problemas.append(f"  - Falta el campo «{campo}».")
        elif detalle["type"] == "extra_forbidden":
            problemas.append(f"  - El campo «{campo}» no existe.")
        else:
            # Never echo the input: it could be the installation credential.
            problemas.append(f"  - El campo «{campo}» no es válido: {detalle['msg']}.")
    return f"El archivo de configuración {ruta} está incompleto:\n" + "\n".join(problemas)
