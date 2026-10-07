"""State machine that turns the pose sequence of one camera into events.

On every frame three conditions are evaluated (rules R1 to R3 of
``docs/classification-spec.md``):

* **M1**: the hip center dropped quickly.
* **M2**: the body lost its vertical alignment (angle with the floor below the threshold).
* **M3**: the body became wider than it is tall, as when someone is lying down.

The three do not happen at the same instant: first the hip drops and the body tilts, and a
moment later the body becomes horizontal. That is why there are three phases:

``NORMAL`` → (M1 and M2) → ``INICIO_CAIDA`` → (M3 within the window) → ``EN_EL_SUELO``

Events emitted:

* ``caida`` (R4): ``EN_EL_SUELO`` was reached.
* ``recuperacion`` (R5): while on the floor, the person is upright again.
* ``caida_confirmada`` (R6): the person is still on the floor after the confirmation time.
* ``movimiento_inestable`` (R7, proposal pending validation): a fall started, but the person
  was upright again before becoming horizontal.
* ``deteccion_no_confiable`` (R8): too much time passed without seeing the person.
"""

from dataclasses import dataclass, field
from enum import StrEnum

from te_tengo_deteccion.clasificacion.medicion import Medicion, MedidorCinematico
from te_tengo_deteccion.clasificacion.umbrales import Umbrales
from te_tengo_deteccion.pose.schemas import Pose


class UmbralSinCalibrarError(ValueError):
    """The speed threshold (R1) is missing; it is obtained by calibrating with datasets."""

    def __init__(self) -> None:
        super().__init__(
            "Falta velocidad_descenso_min: el umbral de velocidad aún no está "
            "calibrado (ver docs/classification-spec.md, regla R1)."
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


@dataclass(frozen=True, slots=True)
class Tiempos:
    """Seconds elapsed in each phase (``None`` if not applicable). Used to display progress."""

    desde_inicio_caida: float | None
    en_el_suelo: float | None
    erguido: float | None


class ClasificadorCinematico:
    """Classifies the pose sequence of ONE camera. ``instante`` is in seconds."""

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
    def umbrales(self) -> Umbrales:
        return self._u

    def tiempos(self, instante: float) -> Tiempos:
        return Tiempos(
            desde_inicio_caida=(
                instante - self._inicio_caida if self._fase is Fase.INICIO_CAIDA else None
            ),
            en_el_suelo=instante - self._instante_caida if self._fase is Fase.EN_EL_SUELO else None,
            erguido=None if self._erguido_desde is None else instante - self._erguido_desde,
        )

    @property
    def ultima_medicion(self) -> Medicion | None:
        """Measurement of the last frame with a pose (to display or log it)."""
        return self._ultima

    def actualizar(self, instante: float, pose: Pose | None) -> list[Evento]:
        """Processes one frame. ``pose`` is ``None`` if nobody was detected."""
        if self._primer_instante is None:
            self._primer_instante = instante
        if pose is None:
            return self._sin_pose(instante)

        self._ultimo_valido = instante
        self._aviso_no_confiable = False
        self._ultima = self._medidor.medir(instante, pose)
        p, velocidad = self._ultima.parametros, self._ultima.velocidad

        m1 = velocidad is not None and velocidad >= self._velocidad_min
        # With the head below the feet (a fall towards the camera) the body is neither vertical
        # nor upright, even if the angle and the ratio do not show it (A7).
        m2 = p.angulo_grados < self._u.angulo_linea_central_max_grados or p.cabeza_bajo_pies
        m3 = p.razon_ancho_alto >= self._u.razon_ancho_alto_min or p.cabeza_bajo_pies
        # "Upright" clears an alert (recovery) or downgrades it (unstable movement), so it is
        # only accepted with the key points clearly visible (A6). The fall conditions do use
        # doubtful poses: a false alarm is preferable to missing a fall.
        erguido = (
            p.puntos_visibles
            and not p.cabeza_bajo_pies
            and p.angulo_grados > self._u.angulo_linea_central_max_grados
            and p.razon_ancho_alto < self._u.razon_ancho_alto_min
        )
        # Recovery requires being seen upright for a minimum time: MediaPipe sometimes estimates
        # a lying person as "standing" for a single isolated frame (A8).
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

    # ------------------------------------------------------------------ internals

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
        # If the person ended up on the floor out of view (for example, behind furniture), the
        # confirmation keeps counting: not seeing them does not mean they got up.
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
