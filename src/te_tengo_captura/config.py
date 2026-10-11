"""The configuration file: an installation's fixed settings, or a linked PC's optional ones.

The file lives in the platform config directory (``platformdirs``, app name ``TeTengoCaptura``)
or is passed with ``--config <ruta>``. The agent has no settings screen.

* **Installation** (until now): the project team writes every field, with the installation
  credential of the camera (``Configuracion``; ``config.ejemplo.toml`` documents them).
* **PC link** (US-28): a new install needs **no file**. The PC asks for a code and the owner
  approves it in the app; its tokens live in the OS credential store. An optional file without
  ``credencial_instalacion`` may only change the API's URL, the classifier and the live view
  (``AjustesPc``).

When the installation's PC is removed from the household, ``olvidar_credencial`` deletes the
credential from the file (contract: "deletes its credentials … and the installation credential
if any"), so the next start shows the link code.
"""

import re
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


def _validar_url(valor: str) -> str:
    if not valor.startswith(("http://", "https://")):
        raise ValueError("debe empezar con http:// o https://")
    return valor.rstrip("/")


def _sobre_calibrados(valor: Any) -> Any:
    # Overrides in [clasificacion] apply on top of the calibrated values, not on top of the
    # uncalibrated defaults of the core.
    if isinstance(valor, dict):
        return {**UMBRALES_CALIBRADOS, **valor}
    return valor


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
        return _validar_url(valor)

    @field_validator("credencial_instalacion")
    @classmethod
    def _credencial_no_vacia(cls, valor: SecretStr) -> SecretStr:
        if not valor.get_secret_value().strip():
            raise ValueError("no puede estar vacía")
        return valor

    @field_validator("clasificacion", mode="before")
    @classmethod
    def _sobre_calibrados(cls, valor: Any) -> Any:
        return _sobre_calibrados(valor)


# Any of these makes the file an installation's, where every field is required.
CAMPOS_DE_INSTALACION = frozenset(
    {"credencial_instalacion", "instalada_el", "webcam", "vivienda", "camara"}
)
API_PREDETERMINADA = "https://api.tetengo.reqsai.tech"  # [implementation choice] production API


class AjustesPc(_Seccion):
    """A linked PC's optional settings: everything else comes from the app."""

    api_url: str = API_PREDETERMINADA
    clasificacion: Umbrales = Umbrales(**UMBRALES_CALIBRADOS)
    vista_en_vivo: VistaEnVivo = VistaEnVivo()

    @field_validator("api_url")
    @classmethod
    def _url_http(cls, valor: str) -> str:
        return _validar_url(valor)

    @field_validator("clasificacion", mode="before")
    @classmethod
    def _sobre_calibrados(cls, valor: Any) -> Any:
        return _sobre_calibrados(valor)


class ConfiguracionInvalidaError(RuntimeError):
    """The installation file is missing, unreadable or has missing or invalid fields."""


def ruta_predeterminada() -> Path:
    """``config.toml`` in the platform config directory (e.g. ``%APPDATA%\\TeTengoCaptura``)."""
    from platformdirs import user_config_path

    return user_config_path(NOMBRE_APP, appauthor=False, roaming=True) / NOMBRE_ARCHIVO


def cargar(ruta: Path | None = None) -> Configuracion | AjustesPc:
    """Reads and validates the file; the error explains, in Spanish, what to fix.

    With no ``--config`` and no file in the default place, the PC is a new install that links
    with a code: the default settings. A file with any installation field
    (``CAMPOS_DE_INSTALACION``) is an installation and every installation field is required, as
    before."""
    if ruta is None and not ruta_predeterminada().is_file():
        return AjustesPc()
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
        if CAMPOS_DE_INSTALACION & datos.keys():
            return Configuracion.model_validate(datos)
        return AjustesPc.model_validate(datos)
    except ValidationError as error:
        raise ConfiguracionInvalidaError(_explicar(ruta, error)) from None


def cargar_instalacion(ruta: Path) -> Configuracion:
    """An installation's file (scripts and tests): an error if it is not one."""
    configuracion = cargar(ruta)
    if not isinstance(configuracion, Configuracion):
        raise ConfiguracionInvalidaError(
            f"El archivo de configuración {ruta} no es de una instalación: "
            "Falta el campo «credencial_instalacion»."
        )
    return configuracion


def olvidar_credencial(ruta: Path) -> None:
    """Deletes the ``credencial_instalacion`` line from the file (the PC left the household)."""
    texto = ruta.read_text(encoding="utf-8")
    nuevo = re.sub(r"(?m)^\s*credencial_instalacion\s*=.*\n?", "", texto)
    if nuevo != texto:
        temporal = ruta.with_suffix(".tmp")
        temporal.write_text(nuevo, encoding="utf-8")
        temporal.replace(ruta)


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
