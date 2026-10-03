"""Máquina de estados que convierte la secuencia de poses de una cámara en eventos.

En cada fotograma se evalúan tres condiciones (reglas R1 a R3 de
``docs/especificacion-clasificacion.md``):

* **M1**: el centro de la cadera bajó rápido.
* **M2**: el cuerpo perdió la vertical (ángulo con el suelo menor que el umbral).
* **M3**: el cuerpo quedó más ancho que alto, como cuando alguien está tendido.

Las tres no ocurren en el mismo instante: primero baja la cadera y se inclina el cuerpo, y un
momento después el cuerpo queda horizontal. Por eso hay tres fases:

``NORMAL`` → (M1 y M2) → ``INICIO_CAIDA`` → (M3 dentro de la ventana) → ``EN_EL_SUELO``

Eventos que se generan:

* ``caida`` (R4): se llegó a ``EN_EL_SUELO``.
* ``recuperacion`` (R5): estando en el suelo, la persona vuelve a estar erguida.
* ``caida_confirmada`` (R6): sigue en el suelo el tiempo de confirmación.
* ``movimiento_inestable`` (R7, propuesta pendiente de validación): empezó a caer, pero volvió
  a estar erguida antes de quedar horizontal.
* ``deteccion_no_confiable`` (R8): pasó demasiado tiempo sin ver a la persona.
"""

from dataclasses import dataclass, field
from enum import StrEnum

from detection_worker.clasificacion.medicion import Medicion, MedidorCinematico
from detection_worker.clasificacion.umbrales import Umbrales
from detection_worker.pose.schemas import Pose


class UmbralSinCalibrarError(ValueError):
    """Falta el umbral de velocidad (R1), que se obtiene calibrando con datasets."""

    def __init__(self) -> None:
        super().__init__(
            "Falta TT_CLASIFICACION__VELOCIDAD_DESCENSO_MIN: el umbral de velocidad aún no está "
            "calibrado (ver docs/especificacion-clasificacion.md, regla R1)."
        )


class TipoEvento(StrEnum):
    CAIDA = "caida"
    CAIDA_CONFIRMADA = "caida_confirmada"
    MOVIMIENTO_INESTABLE = "movimiento_inestable"
    RECUPERACION = "recuperacion"
    DETECCION_NO_CONFIABLE = "deteccion_no_confiable"


class Fase(StrEnum):
    NORMAL = "normal"
    INICIO_CAIDA = "inicio_caida"
    EN_EL_SUELO = "en_el_suelo"


@dataclass(frozen=True, slots=True)
class Evento:
    tipo: TipoEvento
    instante: float
    parametros: dict[str, float] = field(default_factory=dict)


class ClasificadorCinematico:
    """Clasifica la secuencia de poses de UNA cámara. ``instante`` está en segundos."""

    def __init__(self, umbrales: Umbrales) -> None:
        if umbrales.velocidad_descenso_min is None:
            raise UmbralSinCalibrarError
        self._u = umbrales
        self._velocidad_min = umbrales.velocidad_descenso_min
        self._medidor = MedidorCinematico(
            umbrales.intervalo_velocidad_s, umbrales.ventana_velocidad_s, umbrales.visibilidad_min
        )
        self._erguido_desde: float | None = None
        self._ultima: Medicion | None = None
        self._fase = Fase.NORMAL
        self._inicio_caida = 0.0
        self._instante_caida = 0.0
        self._confirmada = False
        self._primer_instante: float | None = None
        self._ultimo_valido: float | None = None
        self._aviso_no_confiable = False

    @property
    def fase(self) -> Fase:
        return self._fase

    @property
    def ultima_medicion(self) -> Medicion | None:
        """Medición del último fotograma con pose (para mostrarla o registrarla)."""
        return self._ultima

    def actualizar(self, instante: float, pose: Pose | None) -> list[Evento]:
        """Procesa un fotograma. ``pose`` es ``None`` si no se detectó a nadie."""
        if self._primer_instante is None:
            self._primer_instante = instante
        if pose is None:
            return self._sin_pose(instante)

        self._ultimo_valido = instante
        self._aviso_no_confiable = False
        self._ultima = self._medidor.medir(instante, pose)
        p, velocidad = self._ultima.parametros, self._ultima.velocidad

        m1 = velocidad is not None and velocidad >= self._velocidad_min
        # Con la cabeza bajo los pies (caída hacia la cámara) el cuerpo no está vertical ni
        # erguido aunque el ángulo y la razón no lo muestren (A7).
        m2 = p.angulo_grados < self._u.angulo_linea_central_max_grados or p.cabeza_bajo_pies
        m3 = p.razon_ancho_alto >= self._u.razon_ancho_alto_min or p.cabeza_bajo_pies
        # «Erguido» apaga una alerta (recuperación) o la rebaja (movimiento inestable), así que
        # solo se acepta con los puntos clave bien visibles (A6). Las condiciones de caída sí
        # usan poses dudosas: es preferible una falsa alarma a perder una caída.
        erguido = (
            p.puntos_visibles
            and not p.cabeza_bajo_pies
            and p.angulo_grados > self._u.angulo_linea_central_max_grados
            and p.razon_ancho_alto < self._u.razon_ancho_alto_min
        )
        # La recuperación exige verse erguido un tiempo mínimo: MediaPipe a veces estima «de pie»
        # a una persona tendida durante un fotograma suelto (A8).
        if not erguido:
            self._erguido_desde = None
        elif self._erguido_desde is None:
            self._erguido_desde = instante
        erguido_sostenido = (
            self._erguido_desde is not None
            and instante - self._erguido_desde >= self._u.persistencia_erguido_s
        )
        datos = {
            "angulo_grados": round(p.angulo_grados, 2),
            "razon_ancho_alto": round(p.razon_ancho_alto, 3),
            "velocidad": round(velocidad, 3) if velocidad is not None else -1.0,
        }

        if self._fase is Fase.NORMAL and m1 and m2:
            self._fase = Fase.INICIO_CAIDA
            self._inicio_caida = instante

        if self._fase is Fase.INICIO_CAIDA:
            if m3:
                return [self._entrar_al_suelo(instante, datos)]
            if erguido:
                self._fase = Fase.NORMAL
                return [Evento(TipoEvento.MOVIMIENTO_INESTABLE, instante, datos)]
            if instante - self._inicio_caida > self._u.ventana_reaccion_s:
                self._fase = Fase.NORMAL
            return []

        if self._fase is Fase.EN_EL_SUELO:
            if erguido_sostenido:
                self._fase = Fase.NORMAL
                return [Evento(TipoEvento.RECUPERACION, instante, datos)]
            return self._revisar_confirmacion(instante, datos)

        return []

    # ------------------------------------------------------------------ internos

    def _entrar_al_suelo(self, instante: float, datos: dict[str, float]) -> Evento:
        self._fase = Fase.EN_EL_SUELO
        self._instante_caida = instante
        self._confirmada = False
        return Evento(TipoEvento.CAIDA, instante, datos)

    def _revisar_confirmacion(self, instante: float, datos: dict[str, float]) -> list[Evento]:
        if (
            self._fase is Fase.EN_EL_SUELO
            and not self._confirmada
            and instante - self._instante_caida >= self._u.confirmacion_suelo_s
        ):
            self._confirmada = True
            return [Evento(TipoEvento.CAIDA_CONFIRMADA, instante, datos)]
        return []

    def _sin_pose(self, instante: float) -> list[Evento]:
        # Si la persona quedó en el suelo fuera de la vista (por ejemplo, detrás de un mueble),
        # la confirmación sigue contando: no verla no significa que se haya levantado.
        eventos = self._revisar_confirmacion(instante, {})
        referencia = (
            self._ultimo_valido if self._ultimo_valido is not None else self._primer_instante
        )
        if (
            referencia is not None
            and not self._aviso_no_confiable
            and instante - referencia >= self._u.sin_deteccion_confiable_s
        ):
            self._aviso_no_confiable = True
            eventos.append(Evento(TipoEvento.DETECCION_NO_CONFIABLE, instante))
        return eventos
