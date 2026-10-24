"""The safe-range sweep (``scripts/barrer_rangos.py``): its statistics and its range rule."""

import importlib
from pathlib import Path
from types import ModuleType

import pytest

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture
def barrido(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.syspath_prepend(str(RAIZ / "scripts"))
    return importlib.import_module("barrer_rangos")


def resumen(barrido: ModuleType, vp: int, vn: int, falsas: int = 0) -> object:
    return barrido.Resumen(vp, 80 - vp, vn, 90 - vn, falsas, 30, 0, (), 0, 0.0)


def test_intervalo_de_wilson(barrido: ModuleType) -> None:
    # 65 of 80: the validated sensitivity, 81.2 % (71.4–88.3 %).
    bajo, alto = barrido.wilson(65, 80)
    assert bajo == pytest.approx(0.7143, abs=1e-3)
    assert alto == pytest.approx(0.8830, abs=1e-3)
    assert barrido.wilson(0, 10)[0] == pytest.approx(0.0)
    assert barrido.wilson(10, 10)[1] == pytest.approx(1.0)


def test_rango_seguro_es_el_tramo_que_contiene_el_valor_por_defecto(barrido: ModuleType) -> None:
    base = resumen(barrido, 65, 73)
    valores = [0.1, 0.2, 0.3, 0.4, 0.5]
    resumenes = [
        resumen(barrido, 50, 80),  # sensitivity below 75 %
        resumen(barrido, 62, 73),  # 3.7 points below: still safe
        base,
        resumen(barrido, 65, 73, falsas=1),  # one false recovery more than the default
        base,  # safe, but not connected to the default
    ]
    assert barrido.rango_seguro(valores, resumenes, 0.3, base) == (0.2, 0.3)
    assert barrido.rango_seguro(valores, resumenes, 0.25, base) is None
