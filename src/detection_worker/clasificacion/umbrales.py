"""Umbrales de la clasificación cinemática.

Se configuran por variable de entorno (``TT_CLASIFICACION__<CAMPO>``). El origen de cada valor
está en la tabla de umbrales de ``docs/especificacion-clasificacion.md``.
"""

from pydantic import BaseModel, Field


class Umbrales(BaseModel):
    model_config = {"frozen": True}

    velocidad_descenso_min: float | None = Field(
        default=None,
        gt=0,
        description=(
            "R1. Velocidad mínima de bajada del centro de la cadera, en cuerpos por segundo. "
            "Sin valor por defecto: se calibra con pruebas. Mientras falte, el servicio arranca "
            "pero no acepta video."
        ),
    )

    angulo_linea_central_max_grados: float = Field(
        default=45.0,
        gt=0,
        lt=90,
        description="R2. Por debajo de este ángulo con el suelo, el cuerpo perdió la vertical.",
    )
    razon_ancho_alto_min: float = Field(
        default=1.0,
        gt=0,
        description="R3. Desde esta razón ancho/alto, el cuerpo está más acostado que de pie.",
    )
    intervalo_velocidad_s: float = Field(
        default=0.25,
        gt=0,
        description="R1. Separación mínima entre las dos muestras con que se mide la velocidad.",
    )
    ventana_reaccion_s: float = Field(
        default=1.48,
        gt=0,
        description=(
            "R4 y R7. Tiempo máximo entre el inicio de la caída y la postura horizontal; si en "
            "ese tiempo la persona vuelve a estar erguida, fue un movimiento inestable."
        ),
    )
    confirmacion_suelo_s: float = Field(
        default=30.0,
        gt=0,
        description="R6. Tiempo en el suelo que confirma la caída.",
    )
    sin_deteccion_confiable_s: float = Field(
        default=300.0,
        gt=0,
        description="R8. Tiempo seguido sin ver a la persona antes de avisar.",
    )
    visibilidad_min: float = Field(
        default=0.5,
        ge=0,
        le=1,
        description="A5. Visibilidad mínima para usar un landmark en el rectángulo del cuerpo.",
    )

    @property
    def calibrado(self) -> bool:
        return self.velocidad_descenso_min is not None
