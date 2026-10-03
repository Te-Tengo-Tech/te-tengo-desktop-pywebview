"""Umbrales de la clasificación cinemática y de dónde sale cada uno.

Toda la trazabilidad (fórmula, fuente y adaptación) está en
``docs/especificacion-clasificacion.md``.
"""

from pydantic import BaseModel, Field


class Umbrales(BaseModel):
    """Valores configurables por variable de entorno (``TT_CLASIFICACION__<CAMPO>``)."""

    model_config = {"frozen": True}

    velocidad_descenso_min: float = Field(
        gt=0,
        description=(
            "Condición M1. Velocidad de descenso del centro de la cadera en longitudes de línea "
            "central por segundo. Adaptación propia: Chen et al. (2020) la dan en m/s con dos "
            "valores contradictorios (0,009 y 0,09), así que no hay valor por defecto y debe "
            "calibrarse con pruebas."
        ),
    )
    angulo_linea_central_max_grados: float = Field(
        default=45.0,
        gt=0,
        lt=90,
        description="Condición M2: θ < 45° (Chen et al., 2020, sección 3.3).",
    )
    razon_ancho_alto_min: float = Field(
        default=1.0,
        gt=0,
        description="Condición M3: P ≥ 1 (Chen et al., 2020, sección 3.4).",
    )
    intervalo_velocidad_s: float = Field(
        default=0.25,
        gt=0,
        description="Δt de la velocidad: cada 5 fotogramas, 0,25 s (Chen et al., 2020, secc. 3.2).",
    )
    ventana_reaccion_s: float = Field(
        default=1.48,
        gt=0,
        description=(
            "Tiempo máximo entre el inicio de la caída (M1 y M2) y la postura horizontal (M3). "
            "Límite superior del tiempo de caída de 1,0 a 1,48 s de Gutiérrez et al. (2023)."
        ),
    )
    confirmacion_suelo_s: float = Field(
        default=30.0,
        gt=0,
        description="Permanencia en el suelo que confirma la caída (US-13 del product backlog).",
    )
    sin_deteccion_confiable_s: float = Field(
        default=300.0,
        gt=0,
        description="Tiempo solo con fotogramas descartados antes de avisar (US-15 del backlog).",
    )
    visibilidad_min: float = Field(
        default=0.5,
        ge=0,
        le=1,
        description=(
            "Visibilidad mínima de un landmark para usarlo. Valor inicial igual a los umbrales por "
            "defecto de MediaPipe (0,5); se calibra con pruebas."
        ),
    )
