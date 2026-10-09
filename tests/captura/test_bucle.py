import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest

from te_tengo_captura.backend.modelos import EventoAgente
from te_tengo_captura.captura.bucle import BucleCaptura, HiloCaptura
from te_tengo_captura.captura.fuentes import Captador, FuenteFalsa, Imagen
from te_tengo_captura.captura.pose import EstimadorMediaPipe
from te_tengo_captura.ids import uuid7
from te_tengo_deteccion.clasificacion.estados import TipoEvento
from te_tengo_deteccion.clasificacion.umbrales import Umbrales
from te_tengo_deteccion.pose.schemas import Pose
from tests import fabricas

PASO = 1 / 8  # the fake webcam delivers exactly 8 fps, so every frame is processed
MODELO = Path("models/pose_landmarker_lite.task")


class EstimadorGrabado:
    """Replays recorded poses, one per frame."""

    def __init__(self, poses: list[Pose | None]) -> None:
        self.poses = poses
        self.llamadas = 0
        self.reinicios = 0

    def estimar(self, imagen: Imagen, instante_ms: int) -> Pose | None:
        self.llamadas += 1
        return self.poses.pop(0) if self.poses else None

    def reiniciar(self) -> None:
        self.reinicios += 1

    def cerrar(self) -> None:
        pass


class BandejaEnMemoria:
    def __init__(self) -> None:
        self.eventos: list[EventoAgente] = []
        self.clips: dict[str, bytes] = {}

    def agregar_evento(self, evento: EventoAgente) -> None:
        self.eventos.append(evento)

    def agregar_clip(self, evento_id: str, mp4: bytes) -> None:
        self.clips[evento_id] = mp4


class Permiso:
    def __init__(self) -> None:
        self.valor = True

    def __call__(self) -> bool:
        return self.valor


class Escenario:
    def __init__(self, umbrales: Umbrales, poses: list[Pose | None]) -> None:
        self.fuente = FuenteFalsa(paso=PASO)
        self.estimador = EstimadorGrabado(poses)
        self.bandeja = BandejaEnMemoria()
        self.permiso = Permiso()
        self.clips_codificados: list[list[float]] = []
        self.encolados = 0
        self.bucle = BucleCaptura(
            Captador(self.fuente, reloj=lambda: 0.0),
            self.estimador,
            umbrales,
            self.bandeja,
            self.permiso,
            al_encolar=self._encolado,
            codificar=self._codificar,
            ejecutar_clip=lambda tarea: tarea(),
            reloj_utc=lambda: datetime(2026, 10, 7, 15, 4, 31, tzinfo=UTC),
        )

    def _encolado(self) -> None:
        self.encolados += 1

    def _codificar(self, fotogramas: list[tuple[float, bytes]]) -> bytes:
        self.clips_codificados.append([t for t, _ in fotogramas])
        return b"mp4"

    def correr(self, pasos: int) -> list[EventoAgente]:
        return [e for _ in range(pasos) for e in self.bucle.paso()]


def caida(segundos_en_el_suelo: int) -> list[Pose | None]:
    poses: list[Pose | None] = [fabricas.DE_PIE] * 9
    return [*poses, fabricas.CAYENDO, *[fabricas.TENDIDA] * (segundos_en_el_suelo * 8)]


def test_una_caida_produce_caida_y_luego_caida_confirmada(umbrales: Umbrales) -> None:
    escenario = Escenario(umbrales, caida(32))
    eventos = escenario.correr(10 + 32 * 8)
    assert [e.tipo for e in eventos] == [TipoEvento.CAIDA, TipoEvento.CAIDA_CONFIRMADA]
    assert escenario.bandeja.eventos == eventos
    caida_ = eventos[0]
    assert uuid.UUID(caida_.evento_id).version == 7
    assert caida_.ocurrido_en == datetime(2026, 10, 7, 15, 4, 31, tzinfo=UTC)
    assert set(caida_.parametros) == {"angulo_grados", "razon_ancho_alto", "velocidad"}


def test_la_caida_lleva_un_clip_de_6_s_antes_y_6_s_despues(umbrales: Umbrales) -> None:
    escenario = Escenario(umbrales, caida(10))
    eventos = escenario.correr(10 + 10 * 8)
    assert len(escenario.clips_codificados) == 1
    instantes = escenario.clips_codificados[0]
    t = 9 * PASO  # instant of the fall
    assert instantes[0] == 0.0  # only 1.1 s existed before the fall
    assert instantes[-1] == pytest.approx(t + 6)
    assert escenario.bandeja.clips == {eventos[0].evento_id: b"mp4"}
    assert escenario.encolados == 2  # the event, then its clip


def test_movimiento_inestable_tambien_lleva_clip(umbrales: Umbrales) -> None:
    poses: list[Pose | None] = [*[fabricas.DE_PIE] * 9, fabricas.TAMBALEO, *[fabricas.DE_PIE] * 60]
    escenario = Escenario(umbrales, poses)
    eventos = escenario.correr(len(poses))
    assert [e.tipo for e in eventos] == [TipoEvento.MOVIMIENTO_INESTABLE]
    assert len(escenario.clips_codificados) == 1


def test_si_el_clip_falla_el_evento_igual_se_envia(umbrales: Umbrales) -> None:
    escenario = Escenario(umbrales, caida(10))

    def fallar(fotogramas: list[tuple[float, bytes]]) -> bytes:
        raise RuntimeError("sin FFmpeg")

    escenario.bucle._codificar = fallar
    escenario.correr(10 + 10 * 8)
    assert [e.tipo for e in escenario.bandeja.eventos] == [TipoEvento.CAIDA]
    assert escenario.bandeja.clips == {}


def test_camara_en_pausa_no_produce_nada_ni_lee_la_webcam(umbrales: Umbrales) -> None:
    escenario = Escenario(umbrales, caida(32))
    escenario.permiso.valor = False
    assert escenario.correr(300) == []
    assert escenario.estimador.llamadas == 0
    assert escenario.fuente.aperturas == 0
    assert not escenario.bucle.activa


def test_al_pausar_se_cierra_la_webcam_y_se_descarta_el_buffer(umbrales: Umbrales) -> None:
    escenario = Escenario(umbrales, caida(10))
    escenario.correr(10)  # the fall happened, its clip is still waiting for the 6 s after
    assert [e.tipo for e in escenario.bandeja.eventos] == [TipoEvento.CAIDA]
    escenario.permiso.valor = False
    escenario.correr(1)
    assert not escenario.fuente.abierta
    assert escenario.estimador.reinicios == 1

    escenario.permiso.valor = True  # resumes on its own (CA-22.3)
    escenario.estimador.poses = [fabricas.TENDIDA for _ in range(80)]
    escenario.correr(80)
    assert escenario.fuente.aperturas == 2
    assert escenario.clips_codificados == []  # the buffer was dropped
    # The classifier was reset: lying down after the pause is not a new fall nor a confirmation.
    assert [e.tipo for e in escenario.bandeja.eventos] == [TipoEvento.CAIDA]


def test_deteccion_no_confiable_se_refleja_hasta_ver_a_la_persona(umbrales: Umbrales) -> None:
    rapido = umbrales.model_copy(update={"sin_deteccion_confiable_s": 2.0})
    poses: list[Pose | None] = [None] * 20 + [fabricas.DE_PIE]
    escenario = Escenario(rapido, poses)
    eventos = escenario.correr(20)
    assert [e.tipo for e in eventos] == [TipoEvento.DETECCION_NO_CONFIABLE]
    assert not escenario.bucle.deteccion_confiable
    escenario.correr(1)
    assert escenario.bucle.deteccion_confiable


def test_webcam_desconectada_no_produce_eventos(umbrales: Umbrales) -> None:
    escenario = Escenario(umbrales, caida(5))
    escenario.fuente.conectada = False
    assert escenario.correr(20) == []
    assert not escenario.bucle.webcam_conectada
    escenario.fuente.conectada = True
    escenario.bucle.buscar_webcam()
    aperturas = escenario.fuente.aperturas
    escenario.correr(1)  # the reopen happens on the next step, not right away
    assert escenario.fuente.aperturas == aperturas + 1
    assert escenario.bucle.webcam_conectada


def test_actualizar_umbrales_reinicia_el_clasificador(umbrales: Umbrales) -> None:
    escenario = Escenario(umbrales, caida(5))
    escenario.correr(10)
    nuevos = umbrales.model_copy(update={"confirmacion_suelo_s": 2.0})
    escenario.bucle.actualizar_umbrales(nuevos)
    assert escenario.bucle.umbrales == umbrales  # applied by the capture thread, on its next step
    escenario.estimador.poses = [fabricas.TENDIDA for _ in range(40)]
    assert escenario.correr(40) == []  # no fall in progress after the reset
    assert escenario.bucle.umbrales == nuevos


def test_hilo_de_captura_procesa_y_se_detiene(umbrales: Umbrales) -> None:
    escenario = Escenario(umbrales, caida(1))
    listo = threading.Event()
    escenario.bucle._al_encolar = listo.set
    hilo = HiloCaptura(escenario.bucle)
    hilo.iniciar()
    assert listo.wait(5)
    hilo.despertar()
    hilo.detener()
    assert not escenario.fuente.abierta


def test_uuid7_ordenado_por_tiempo() -> None:
    a = uuid7(reloj_ms=lambda: 1_700_000_000_000, aleatorio=lambda n: b"\xff" * n)
    b = uuid7(reloj_ms=lambda: 1_700_000_000_001, aleatorio=lambda n: b"\x00" * n)
    assert a < b
    for valor in (a, b, uuid7()):
        u = uuid.UUID(valor)
        assert (u.version, u.variant) == (7, uuid.RFC_4122)
    assert int(a.replace("-", "")[:12], 16) == 1_700_000_000_000


@pytest.mark.integracion
@pytest.mark.skipif(not MODELO.is_file(), reason="Falta el modelo: ejecuta `make modelo`")
def test_estimador_mediapipe_sin_personas() -> None:
    estimador = EstimadorMediaPipe(MODELO)
    negro: Imagen = np.zeros((480, 640, 3), dtype=np.uint8)
    assert estimador.estimar(negro, 0) is None
    assert estimador.estimar(negro, 125) is None
    assert estimador.estimar(negro, 50) is None  # timestamps went back: new tracker
    estimador.cerrar()


def test_estimador_mediapipe_sin_modelo(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        EstimadorMediaPipe(tmp_path / "no.task")


def test_sin_permiso_la_webcam_no_figura_desconectada(umbrales: Umbrales) -> None:
    escenario = Escenario(umbrales, [])
    escenario.permiso.valor = False
    escenario.correr(3)
    assert escenario.bucle.webcam_conectada


def test_un_error_inesperado_reinicia_la_captura_y_se_muestra_como_problema(
    umbrales: Umbrales, monkeypatch: pytest.MonkeyPatch
) -> None:
    from te_tengo_captura.captura import bucle as modulo

    monkeypatch.setattr(modulo, "ESPERA_ERROR_INICIAL_S", 0.01)
    escenario = Escenario(umbrales, [])
    fallos = {"n": 2}
    vistos: list[bool] = []
    recuperada = threading.Event()
    original = escenario.estimador.estimar

    def estimar(imagen: Imagen, instante_ms: int) -> Pose | None:
        if fallos["n"] > 0:
            fallos["n"] -= 1
            raise RuntimeError("MediaPipe falló")
        vistos.append(escenario.bucle.webcam_conectada)
        recuperada.set()
        return original(imagen, instante_ms)

    escenario.estimador.estimar = estimar  # type: ignore[method-assign]
    hilo = HiloCaptura(escenario.bucle)
    hilo.iniciar()
    assert recuperada.wait(5)
    hilo.detener()
    assert hilo.errores == 2
    assert escenario.estimador.reinicios >= 2  # the tracker was reset after each error
    assert escenario.fuente.aperturas >= 3  # the webcam was reopened
    assert vistos[0] is False  # reported as a problem until a frame goes through
    assert escenario.bucle.webcam_conectada


def test_mientras_falla_la_webcam_figura_desconectada(umbrales: Umbrales) -> None:
    escenario = Escenario(umbrales, [])
    escenario.correr(1)
    escenario.bucle.reiniciar_tras_error()
    assert not escenario.bucle.webcam_conectada
    escenario.correr(2)
    assert escenario.bucle.webcam_conectada


class EnVivoGrabado:
    def __init__(self) -> None:
        self.activo = False
        self.instantes: list[float] = []
        self.poses: list[Pose | None] = []
        self.suspensiones = 0

    def ofrecer(self, instante: float, imagen: Imagen) -> None:
        self.instantes.append(instante)

    def anotar_pose(self, pose: Pose | None) -> None:
        self.poses.append(pose)

    def suspender(self) -> None:
        self.suspensiones += 1


def test_la_vista_en_vivo_recibe_las_poses_solo_si_alguien_mira(umbrales: Umbrales) -> None:
    escenario = Escenario(umbrales, [])
    en_vivo = EnVivoGrabado()
    escenario.bucle._en_vivo = en_vivo
    escenario.correr(3)
    assert en_vivo.poses == []
    en_vivo.activo = True
    escenario.correr(2)
    assert len(en_vivo.poses) == 2
    escenario.permiso.valor = False  # paused: no live view (CA-23.4)
    escenario.correr(5)
    assert len(en_vivo.poses) == 2
    assert en_vivo.suspensiones == 1  # the publisher is told at once


def test_la_vista_en_vivo_recibe_la_pose_ya_estimada_del_fotograma(umbrales: Umbrales) -> None:
    pose = fabricas.DE_PIE
    escenario = Escenario(umbrales, [pose, None])
    en_vivo = EnVivoGrabado()
    en_vivo.activo = True
    escenario.bucle._en_vivo = en_vivo
    escenario.correr(2)
    assert en_vivo.poses == [pose, None]
    assert escenario.estimador.llamadas == 2  # the live view never estimates again


def test_transmisor_nulo() -> None:
    from te_tengo_captura.captura.en_vivo import TransmisorNulo

    nulo = TransmisorNulo()
    assert not nulo.activo
    nulo.ofrecer(0.0, np.zeros((1, 1, 3), dtype=np.uint8))
    nulo.anotar_pose(None)
    nulo.suspender()
