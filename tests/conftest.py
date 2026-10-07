from collections.abc import Iterator

import pytest

from detection_worker.clasificacion.umbrales import Umbrales
from detection_worker.config import Settings
from detection_worker.eventos.schemas import EventoDetectado
from detection_worker.ingesta.buffer import Clip
from detection_worker.pose.schemas import Pose

TOKEN_INGESTA = "token-de-prueba"


@pytest.fixture
def umbrales() -> Umbrales:
    # The minimum speed is only for the tests: the real value is calibrated (see the spec).
    return Umbrales(velocidad_descenso_min=0.5)


@pytest.fixture
def settings(umbrales: Umbrales) -> Settings:
    return Settings(
        _env_file=None,
        ingesta_token=TOKEN_INGESTA,
        backend_url="http://backend.test",
        backend_token="token-backend",
        clips_bucket="clips-prueba",
        clasificacion=umbrales,
    )


class EstimadorFalso:
    """Returns the poses from a list, in order; ``None`` simulates a discarded frame."""

    def __init__(self, poses: list[Pose | None] | None = None) -> None:
        self._poses: Iterator[Pose | None] = iter(poses or [])

    async def estimar(self, jpeg: bytes, camara_id: str, instante_ms: int) -> Pose | None:
        return next(self._poses, None)

    async def liberar(self, camara_id: str) -> None:
        pass

    def cerrar(self) -> None:
        pass


class PublicadorFalso:
    def __init__(self) -> None:
        self.eventos: list[EventoDetectado] = []
        self.clips: dict[str, str] = {}

    async def publicar(self, evento: EventoDetectado) -> None:
        self.eventos.append(evento)

    async def asociar_clip(self, evento_id: str, clave: str) -> None:
        self.clips[evento_id] = clave

    async def cerrar(self) -> None:
        pass


class AlmacenFalso:
    def __init__(self) -> None:
        self.guardados: list[Clip] = []

    async def guardar(self, camara_id: str, clip: Clip) -> str:
        self.guardados.append(clip)
        return f"clips/{camara_id}/{clip.evento_id}.mp4"
