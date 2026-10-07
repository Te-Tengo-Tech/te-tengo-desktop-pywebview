from collections.abc import Iterator

from te_tengo_captura.captura.procesador import EventoDetectado, ProcesadorCamara
from te_tengo_deteccion.clasificacion.estados import ClasificadorCinematico, TipoEvento
from te_tengo_deteccion.clasificacion.umbrales import Umbrales
from te_tengo_deteccion.clips.buffer import Clip
from te_tengo_deteccion.pose.schemas import Pose
from tests import fabricas

JPEG = b"\xff\xd8\xff\xe0contenido"


class EstimadorFalso:
    """Returns the poses from a list, in order; ``None`` simulates a discarded frame."""

    def __init__(self, poses: list[Pose | None]) -> None:
        self._poses: Iterator[Pose | None] = iter(poses)

    async def estimar(self, jpeg: bytes, camara_id: str, instante_ms: int) -> Pose | None:
        return next(self._poses, None)

    async def liberar(self, camara_id: str) -> None:
        pass

    def cerrar(self) -> None:
        pass


class PublicadorFalso:
    def __init__(self) -> None:
        self.eventos: list[EventoDetectado] = []

    async def publicar(self, evento: EventoDetectado) -> None:
        self.eventos.append(evento)


class ClipsFalsos:
    def __init__(self) -> None:
        self.guardados: list[Clip] = []

    async def guardar(self, clip: Clip) -> None:
        self.guardados.append(clip)


async def test_caida_se_publica_y_su_clip_se_guarda(umbrales: Umbrales) -> None:
    instantes = (
        [round(i * 0.1, 1) for i in range(11)]
        + [1.1]
        + [round(1.2 + i * 0.5, 1) for i in range(14)]
    )
    poses: list[Pose | None] = [fabricas.DE_PIE] * 11
    poses += [fabricas.CAYENDO] + [fabricas.TENDIDA] * 14
    publicador, clips = PublicadorFalso(), ClipsFalsos()
    procesador = ProcesadorCamara(
        "camara-1", EstimadorFalso(poses), ClasificadorCinematico(umbrales), publicador, clips
    )

    for t in instantes:
        await procesador.procesar(int(t * 1000), JPEG)
    await procesador.cerrar()

    assert [e.tipo for e in publicador.eventos] == [TipoEvento.CAIDA]
    assert [c.evento_id for c in clips.guardados] == [publicador.eventos[0].evento_id]
