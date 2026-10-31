"""The GMDCSA24 hold-out test (``scripts/evaluar.py``, ``scripts/evaluar_holdout.py``)."""

import importlib
from pathlib import Path
from types import ModuleType

import pytest

from te_tengo_captura.config import UMBRALES_CALIBRADOS

RAIZ = Path(__file__).resolve().parents[1]

FALL_CSV = (
    "File Name,Length (seconds),Time of Recording,Attire,Description, Classes\n"
    "01.mp4,06, Day (Light On),Shirt, Walking to falling. Right side fall, "
    "Falling (SW)[1.8 to 5]:; Walking[0 to 1.8]\n"
    "02.mp4,10,Night,Shirt,Falling from bed to ground, Falling (BW[5.9 to 10]; Walking[0 to 1.3]\n"
    "03.mp4,04,Day,Shirt,Falling (FW) on the floor, Falling (FW); Sitting[0 to 1.7]"
)
ADL_CSV = (
    "File Name,Length (seconds),Time of Recording,Attire,Description, Classes\n"
    "01.mp4,08, Day, Shirt, Sitting on the bed to sleeping on the bed, Sitting[0 to 1]; "
    "Sleeping[2 to 8]\n"
    "02.mp4,07,Day,Shirt,Doing exercise (push-up); view 1, Exercising[2.6 to 7]\n"
    "03.mp4,06,Day,Shirt,Walking in the room, Walking[0 to 6]"
)


@pytest.fixture
def scripts(monkeypatch: pytest.MonkeyPatch) -> tuple[ModuleType, ModuleType]:
    monkeypatch.syspath_prepend(str(RAIZ / "scripts"))
    return importlib.import_module("evaluar"), importlib.import_module("evaluar_holdout")


def _dataset(raiz: Path) -> None:
    sujeto = raiz / "gmdcsa24" / "v2.1" / "Subject 2"
    for clase, texto in (("Fall", FALL_CSV), ("ADL", ADL_CSV)):
        (sujeto / clase).mkdir(parents=True)
        (sujeto / f"{clase}.csv").write_text(texto, encoding="utf-8")
        for i in (1, 2, 3):
            (sujeto / clase / f"{i:02d}.mp4").write_bytes(b"")


def test_gmdcsa24_lee_carpetas_etiquetas_e_inicio(
    scripts: tuple[ModuleType, ModuleType], tmp_path: Path
) -> None:
    evaluar, _ = scripts
    _dataset(tmp_path)
    videos = {v.nombre: v for v in evaluar.listar_videos(tmp_path, ["gmdcsa24"])}
    assert sorted(videos) == [f"S2-{c}-0{i}" for c in ("ADL", "Fall") for i in (1, 2, 3)]
    caida = videos["S2-Fall-01"]
    assert caida.es_caida
    assert caida.grupo == "gmdcsa24-S2"
    assert caida.inicio_caida == pytest.approx(1.8)
    assert caida.actividad == "fall sideways"
    assert caida.se_levanta is False  # walking ends before the fall onset
    assert videos["S2-Fall-02"].inicio_caida == pytest.approx(5.9)  # "(BW[" typo in the labels
    assert videos["S2-Fall-03"].inicio_caida is None  # no interval given
    assert videos["S2-ADL-01"].actividad == "lying down on / getting up from the bed"
    assert videos["S2-ADL-02"].actividad == "exercise (push-ups, bending, arms)"
    assert videos["S2-ADL-03"].actividad == "walking or standing"
    assert not any(v.es_caida for v in videos.values() if "-ADL-" in v.nombre)


def test_por_defecto_no_se_mezcla_con_la_calibracion(
    scripts: tuple[ModuleType, ModuleType], tmp_path: Path
) -> None:
    evaluar, _ = scripts
    _dataset(tmp_path)
    assert evaluar.listar_videos(tmp_path) == []  # only URFD and CAUCAFall by default


def test_umbrales_congelados_son_los_del_agente(scripts: tuple[ModuleType, ModuleType]) -> None:
    _, holdout = scripts
    assert (
        holdout.CONGELADOS.velocidad_descenso_min == UMBRALES_CALIBRADOS["velocidad_descenso_min"]
    )
    por_defecto = type(holdout.CONGELADOS)(**UMBRALES_CALIBRADOS)
    assert por_defecto == holdout.CONGELADOS


def test_criterio_con_inicio_ignora_caidas_previas(
    scripts: tuple[ModuleType, ModuleType], tmp_path: Path
) -> None:
    evaluar, holdout = scripts
    _dataset(tmp_path)
    video = next(
        v for v in evaluar.listar_videos(tmp_path, ["gmdcsa24"]) if v.nombre == "S2-Fall-02"
    )
    temprana = [("caida", 2.3)]  # lying on the bed, 3.6 s before the labelled fall
    assert holdout.detecto(temprana)
    assert not holdout.a_tiempo(video, temprana)
    assert holdout.a_tiempo(video, [("caida", 2.3), ("caida", 5.2)])  # within 1 s of the onset
    c = holdout.Conteo(72, 7, 53, 28)
    assert c.precision == pytest.approx(72 / 100)
    assert c.f1 == pytest.approx(2 * 0.72 * (72 / 79) / (0.72 + 72 / 79))
