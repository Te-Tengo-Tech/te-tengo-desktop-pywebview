"""The UP-Fall and MCFD hold-out loaders (``scripts/evaluar.py``, ``scripts/evaluar_multicamara.py``)."""

import importlib
import itertools
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from te_tengo_captura.captura.fuentes import Muestreador

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture
def evaluar(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.syspath_prepend(str(RAIZ / "scripts"))
    return importlib.import_module("evaluar")


@pytest.fixture
def multicamara(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.syspath_prepend(str(RAIZ / "scripts"))
    return importlib.import_module("evaluar_multicamara")


def _upfall(raiz: Path) -> None:
    for nombre in (
        "Subject1Activity1Trial1Camera1",
        "Subject1Activity1Trial1Camera2",
        "Subject12Activity11Trial1Camera2",
        "Subject3Activity9Trial1Camera1",
    ):
        carpeta = raiz / "upfall" / nombre
        carpeta.mkdir(parents=True)
        for marca in ("2018-07-04T12_04_17.738369", "2018-07-04T12_04_17.790509"):
            (carpeta / f"{marca}.png").write_bytes(b"")
    (raiz / "upfall" / "notas.txt").write_text("not a recording", encoding="utf-8")
    (raiz / "upfall" / "Subject1Activity1Trial1Camera2Synced").mkdir()


def test_upfall_verdad_por_actividad_grupo_y_ensayo(evaluar: ModuleType, tmp_path: Path) -> None:
    _upfall(tmp_path)
    videos = {v.nombre: v for v in evaluar.listar_videos(tmp_path, ["upfall"])}
    assert sorted(videos) == ["S01-A01-T1-C1", "S01-A01-T1-C2", "S03-A09-T1-C1", "S12-A11-T1-C2"]
    caida = videos["S01-A01-T1-C2"]
    assert caida.es_caida
    assert caida.actividad == "falling forward using hands"
    assert caida.grupo == "upfall-S01"
    assert caida.ensayo == videos["S01-A01-T1-C1"].ensayo == "S01-A01-T1"
    assert caida.camara == "camera 2 (frontal view)"
    assert not videos["S12-A11-T1-C2"].es_caida
    assert videos["S12-A11-T1-C2"].actividad == "laying"
    assert not videos["S03-A09-T1-C1"].es_caida
    assert videos["S03-A09-T1-C1"].camara == "camera 1 (lateral view)"


def test_upfall_no_se_mezcla_por_defecto(evaluar: ModuleType, tmp_path: Path) -> None:
    _upfall(tmp_path)
    assert evaluar.listar_videos(tmp_path) == []


def test_upfall_instantes_desde_los_nombres(evaluar: ModuleType, tmp_path: Path) -> None:
    for nombre in (
        "2018-07-04T12_04_18.000000.png",
        "2018-07-04T12_04_17.500000.png",
        "2018-07-04T12_04_17.500000 - copi.png",  # duplicated frame in one zip
        "2018-07-04T12_04_17.250000.png",
    ):
        (tmp_path / nombre).write_bytes(b"")
    instantes = [(round(t, 6), r.name) for t, r in evaluar.fotogramas_upfall(tmp_path)]
    assert instantes == [
        (0.0, "2018-07-04T12_04_17.250000.png"),
        (0.25, "2018-07-04T12_04_17.500000.png"),
        (0.75, "2018-07-04T12_04_18.000000.png"),
    ]


def test_upfall_muestreo_por_marcas_de_tiempo_como_el_agente(
    evaluar: ModuleType, tmp_path: Path
) -> None:
    # About 18 Hz with a 0.8 s gap (as in the dataset): the sampler restarts after the gap.
    instantes = [round(i * 0.055, 3) for i in range(20)] + [
        round(1.85 + i * 0.055, 3) for i in range(5)
    ]
    for t in instantes:
        segundos = 17 + t
        (
            tmp_path / f"2018-07-04T12_04_{int(segundos):02d}.{round(segundos % 1 * 1e6):06d}.png"
        ).write_bytes(b"")
    video = evaluar.Video("upfall", "x", tmp_path, True, "a", "g")
    muestreador = Muestreador(8.0)
    tomados = [round(t, 3) for t, _ in evaluar.fuente_validacion(video) if muestreador.tomar(t)]
    assert tomados == [0.0, 0.165, 0.275, 0.385, 0.55, 0.66, 0.77, 0.88, 1.045, 1.85, 2.015]


def test_mcfd_periodos_en_la_camara_con_retardo_y_errata(evaluar: ModuleType) -> None:
    # Scenario 1: reference camera "11" is camera 8 (erratum), falling at frames 1080–1108.
    ref = next(p for p in evaluar.periodos_mcfd(1, 8) if p.codigo == 2)
    assert ref.desde == pytest.approx(1080 / 30)
    assert ref.hasta == pytest.approx(1109 / 30)
    # Camera 5 has 23 more frames at the start (the cameras end together).
    otra = next(p for p in evaluar.periodos_mcfd(1, 5) if p.codigo == 2)
    assert otra.desde == pytest.approx((1080 + 23) / 30)
    # Scenario 2 (reference camera 4), corrected by the erratum: falling at 395–425.
    caida = next(p for p in evaluar.periodos_mcfd(2, 4) if p.codigo == 2)
    assert (caida.desde, caida.hasta) == (pytest.approx(395 / 30), pytest.approx(426 / 30))
    assert evaluar.RETARDOS_MCFD[5][4] == 18  # scenario 5, camera 5 (erratum)


def test_mcfd_tablas_coherentes(evaluar: ModuleType) -> None:
    assert sorted(evaluar.ETIQUETAS_MCFD) == sorted(evaluar.RETARDOS_MCFD) == list(range(1, 25))
    for escenario, (referencia, periodos) in evaluar.ETIQUETAS_MCFD.items():
        assert 1 <= referencia <= 8
        assert len(evaluar.RETARDOS_MCFD[escenario]) == 8
        assert all(a <= b for a, b, _ in periodos)
        assert all(b < c for (_, b, _), (c, _, _) in itertools.pairwise(periodos))
        caidas = sum(c == 2 for _, _, c in periodos)
        assert caidas == {4: 2, 23: 2, 24: 0}.get(escenario, 1)


def test_mcfd_ventanas_de_caida(evaluar: ModuleType) -> None:
    periodos = evaluar.periodos_mcfd(4, 6)  # two falls, the person gets up in between
    ventanas = evaluar.caidas_mcfd(periodos)
    assert ventanas == [
        (pytest.approx(288 / 30), pytest.approx(381 / 30)),
        (pytest.approx(601 / 30), pytest.approx(781 / 30)),  # ends with the labels
    ]
    # Scenario 23: each "falling" is followed by "moving up", so the window is the period itself.
    silla, sofa = evaluar.caidas_mcfd(evaluar.periodos_mcfd(23, 8))
    assert silla == (pytest.approx(1520 / 30), pytest.approx(1596 / 30))
    assert sofa == (pytest.approx(3574 / 30), pytest.approx(3615 / 30))


def test_mcfd_videos(evaluar: ModuleType, tmp_path: Path) -> None:
    for escenario in (1, 23):
        for camara in (1, 8):
            ruta = tmp_path / "mcfd" / f"chute{escenario:02d}" / f"cam{camara}.avi"
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_bytes(b"")
    videos = {v.nombre: v for v in evaluar.listar_videos(tmp_path, ["mcfd"])}
    assert sorted(videos) == ["chute01-cam1", "chute01-cam8", "chute23-cam1", "chute23-cam8"]
    v = videos["chute01-cam1"]
    assert v.es_caida
    assert v.fps_fuente == 30.0
    assert v.grupo == "mcfd"
    assert v.ensayo == "chute01"
    assert v.inicio_caida == pytest.approx((1080 - 0 + 3) / 30)
    assert v.detalle == "walking, standing up → moving up → falling → lying on the ground"
    assert not videos["chute23-cam8"].es_caida
    assert videos["chute23-cam8"].inicio_caida is None


def test_fusion_or_por_ensayo(evaluar: ModuleType, multicamara: ModuleType) -> None:
    def video(nombre: str, ensayo: str, camara: str, caida: bool) -> object:
        return evaluar.Video(
            "upfall", nombre, Path(nombre), caida, "a", "g", camara=camara, ensayo=ensayo
        )

    videos = [
        video("a1", "A", "c1", True),
        video("a2", "A", "c2", True),
        video("b1", "B", "c1", True),
        video("b2", "B", "c2", True),
        video("n1", "N", "c1", False),
        video("n2", "N", "c2", False),
    ]
    alarma = {"a1": False, "a2": True, "b1": False, "b2": False, "n1": False, "n2": True}
    o = multicamara.contar_fusion(videos, lambda v: alarma[v.nombre])
    assert (o.vp, o.fn, o.vn, o.fp) == (1, 1, 0, 1)
    solo_c1 = multicamara.contar_fusion(videos, lambda v: alarma[v.nombre], {"c1"})
    assert (solo_c1.vp, solo_c1.fn, solo_c1.vn, solo_c1.fp) == (0, 2, 1, 0)
    y = multicamara.contar_y(videos, lambda v: alarma[v.nombre])
    assert (y.vp, y.fn, y.vn, y.fp) == (0, 2, 1, 0)


def test_fundir_alarmas_cercanas(multicamara: ModuleType) -> None:
    assert multicamara.fundir([]) == 0
    assert multicamara.fundir([10.0, 12.0, 14.9, 15.1, 40.0]) == 3  # 10, 15.1 and 40


def test_ventanas_tolerancia_y_codigo(multicamara: ModuleType) -> None:
    w = multicamara.Ventanas(((10.0, 20.0),), ((50.0, 56.0),), ((0.0, 10.0, 1), (10.0, 11.0, 2)))
    assert w.en_caida(9.1) == 0  # up to 1 s before the labelled onset
    assert w.en_caida(8.9) is None
    assert w.en_caida(20.0) == 0
    assert w.en_ambigua(49.5)
    assert w.codigo(5.0) == "walking, standing up"
    assert w.codigo(30.0).startswith("unlabelled")
    assert w.etiquetado == (0.0, 11.0)
    assert w.en_etiquetado(11.0)
    assert not w.en_etiquetado(11.5)


def test_evento_mcfd_por_camara_y_fusion(evaluar: ModuleType, multicamara: ModuleType) -> None:
    def video(camara: int) -> Any:
        return evaluar.Video(
            "mcfd",
            f"chute01-cam{camara}",
            Path("x.avi"),
            True,
            "scenario 1",
            "mcfd",
            camara=f"camera {camara}",
            ensayo="chute01",
        )

    videos = [video(1), video(8)]
    ventanas = {v.nombre: multicamara.ventanas_mcfd(v) for v in videos}
    inicio8 = 1080 / 30  # camera 8 is the reference; camera 1 starts 3 frames earlier
    eventos = {
        # Camera 8: detects the fall, one false alarm at 31 s and one after the labels end.
        "chute01-cam8": [("caida", 31.0), ("caida", inicio8 + 0.5), ("caida", 50.0)],
        # Camera 1: the same false alarm 1 s later on the common timeline; misses the fall.
        "chute01-cam1": [("caida", 31.0 + 3 / 30 + 1.0)],
    }
    solo8 = multicamara.evento(videos, eventos, ventanas, {8})
    assert (solo8.caidas, solo8.detectadas, solo8.falsas, solo8.sin_etiqueta) == (1, 1, 1, 1)
    solo1 = multicamara.evento(videos, eventos, ventanas, {1})
    assert (solo1.detectadas, solo1.falsas) == (0, 1)
    ambas = multicamara.evento(videos, eventos, ventanas, {1, 8})
    assert (ambas.detectadas, ambas.falsas) == (1, 1)  # merged: closer than FUSION_S
    inicio, fin = ventanas["chute01-cam8"].etiquetado
    ventana = ventanas["chute01-cam8"].caidas[0]
    assert solo8.horas_sin_caida * 3600 == pytest.approx((fin - inicio) - (ventana[1] - ventana[0]))
