"""Parity between the desktop agent and the validation pipeline (docs/validation.md, section 2).

The published sensitivity and specificity describe the agent only if it gives MediaPipe the same
images, at the same timestamps and with the same options as ``scripts/evaluar.py``. These tests
run both paths through ``scripts/comparar_pipelines.py``:

* always: on a synthetic video, with MediaPipe replaced by a recorder (sampling, crop, 480p,
  JPEG, colour order, timestamps and landmarker options must match byte for byte);
* with the model and the URFD clip (``make modelo``, ``make datasets``): the real poses, the
  classifier phase and the ``caida`` event of ``fall-01`` must match frame by frame.
"""

import hashlib
import importlib
from pathlib import Path
from types import ModuleType
from typing import Any

import cv2
import numpy as np
import pytest

import te_tengo_captura.captura.pose as pose_agente
import te_tengo_deteccion.pose.service as servicio
from te_tengo_captura.config import UMBRALES_CALIBRADOS
from te_tengo_deteccion.clasificacion.umbrales import Umbrales

RAIZ = Path(__file__).resolve().parents[2]
MODELO = RAIZ / "models" / "pose_landmarker_lite.task"
FALL_01 = RAIZ / "datos" / "urfd" / "fall-01-cam0.mp4"


@pytest.fixture
def scripts(monkeypatch: pytest.MonkeyPatch) -> tuple[ModuleType, ModuleType]:
    monkeypatch.syspath_prepend(str(RAIZ / "scripts"))
    return importlib.import_module("evaluar"), importlib.import_module("comparar_pipelines")


def _video_sintetico(ruta: Path, fps: float = 25.0, segundos: float = 3.0) -> None:
    """Depth + colour halves like URFD, but 1280 × 960 so the crop must be downscaled to 480p."""
    salida = cv2.VideoWriter(str(ruta), cv2.VideoWriter.fourcc(*"FFV1"), fps, (1280, 960))
    generador = np.random.default_rng(7)
    for i in range(round(fps * segundos)):
        imagen = generador.integers(0, 256, (960, 1280, 3), dtype=np.uint8)
        imagen[:, 640:, 0] = (i * 9) % 256  # a colour that changes per frame, in B only
        salida.write(imagen)
    salida.release()


class _Grabadora:
    """Stands in for MediaPipe and records what each path sends it."""

    def __init__(self) -> None:
        self.opciones: list[tuple[str, float, str]] = []
        self.fotogramas: list[tuple[int | None, tuple[int, ...], str, str]] = []

    def crear(self, ruta: str, confianza_min: float = 0.5, modo: str = "imagen") -> Any:
        self.opciones.append((Path(ruta).name, confianza_min, modo))
        return self

    def detectar(self, landmarker: Any, imagen: Any, instante_ms: int | None = None) -> None:
        huella = hashlib.sha256(imagen.tobytes()).hexdigest()
        self.fotogramas.append((instante_ms, imagen.shape, str(imagen.dtype), huella))
        return None

    def close(self) -> None:
        pass


def test_el_agente_da_a_mediapipe_lo_mismo_que_la_validacion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scripts: tuple[ModuleType, ModuleType],
) -> None:
    evaluar, comparar = scripts
    ruta = tmp_path / "sintetico.avi"
    _video_sintetico(ruta)
    modelo = tmp_path / "pose_landmarker_lite.task"
    modelo.write_bytes(b"")
    video = evaluar.Video("urfd", "sintetico", ruta, True, "caída", "urfd", (640, 0, 640, 960))
    umbrales = Umbrales(**UMBRALES_CALIBRADOS)

    grabaciones = []
    for camino in ("validacion", "agente"):
        grabadora = _Grabadora()
        for modulo in (servicio, pose_agente):
            monkeypatch.setattr(modulo, "crear_landmarker", grabadora.crear)
            monkeypatch.setattr(modulo, "detectar", grabadora.detectar)
        if camino == "validacion":
            registros = comparar.por_validacion(video, modelo, umbrales)
        else:
            registros = comparar.por_agente(ruta, video.recorte, modelo, umbrales)
        assert len(registros) == len(grabadora.fotogramas)
        grabaciones.append(grabadora)

    validacion, agente = grabaciones
    assert len(validacion.fotogramas) == 24  # 3 s at 8 fps
    assert {f[1] for f in validacion.fotogramas} == {(480, 320, 3)}
    assert agente.fotogramas == validacion.fotogramas
    assert agente.opciones == validacion.opciones == [("pose_landmarker_lite.task", 0.5, "video")]


@pytest.mark.integracion
@pytest.mark.skipif(not MODELO.is_file(), reason="Falta el modelo: ejecuta `make modelo`")
@pytest.mark.skipif(not FALL_01.is_file(), reason="Falta URFD: ejecuta `make datasets`")
def test_fall_01_da_las_mismas_poses_y_la_misma_caida(
    scripts: tuple[ModuleType, ModuleType],
) -> None:
    evaluar, comparar = scripts
    video = next(v for v in evaluar.listar_videos(RAIZ / "datos") if v.nombre == "fall-01")
    iguales, informe = comparar.comparar_video(video, MODELO, False, True, None)
    assert iguales, informe
    assert "eventos [(4767, 'caida')] = validacion" in informe


def test_el_agente_no_cambia_la_confianza_de_mediapipe_con_visibilidad_min(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from te_tengo_captura import __main__ as principal
    from te_tengo_captura.config import cargar

    creados: list[float] = []
    monkeypatch.setattr(
        principal,
        "EstimadorMediaPipe",
        lambda ruta, confianza_min=0.5: creados.append(confianza_min),
    )
    monkeypatch.setattr(principal, "Agente", lambda *args, **kwargs: None)
    config = tmp_path / "config.toml"
    ejemplo = (RAIZ / "config.ejemplo.toml").read_text(encoding="utf-8")
    config.write_text(ejemplo + "\n[clasificacion]\nvisibilidad_min = 0.8\n", encoding="utf-8")
    args = principal.argumentos(["--backend-falso", "--config", str(config)])
    principal.construir_agente(args, cargar(config))
    assert creados == [0.5]
