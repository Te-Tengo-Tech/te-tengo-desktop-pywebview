"""Selection rules of scripts/evaluar_lodo.py (ADR 0011)."""

import importlib
from pathlib import Path
from types import ModuleType

import pytest

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture
def m(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.syspath_prepend(str(RAIZ / "scripts"))
    return importlib.import_module("evaluar_lodo")


def test_familias_tienen_las_rejillas_registradas(m: ModuleType) -> None:
    f = m.familias()
    assert {n: len(a) for n, a in f.items()} == {
        "baseline": 100,
        "F1": 500,
        "F2": 500,
        "F1+F2": 2500,
        "F3": 500,
    }
    assert all(a["erguido_previo_exige_visibles"] is False for a in f["F3"])


def test_youden_desempata_por_la_velocidad_mas_baja_y_la_ventana_mas_larga(m: ModuleType) -> None:
    ajustes = [
        {"velocidad_descenso_min": 0.2, "erguido_previo_caida_s": 10.0},
        {"velocidad_descenso_min": 0.1, "erguido_previo_caida_s": 3.0},
        {"velocidad_descenso_min": 0.1, "erguido_previo_caida_s": 10.0},
    ]
    igual = {"a": m.Cuenta(8, 10, 8, 10), "b": m.Cuenta(6, 10, 9, 10)}
    assert m.elegir("youden", ajustes, [igual] * 3, ["a", "b"]) == 2


def test_criterio_de_sensibilidad_minima(m: ModuleType) -> None:
    a = {"velocidad_descenso_min": 0.1}
    # Below 90 %: the higher sensitivity wins; at or above 90 %: the higher specificity.
    assert m.clave("spec_sens90", 0.85, 0.9, a) < m.clave("spec_sens90", 0.88, 0.5, a)
    assert m.clave("spec_sens90", 0.95, 0.5, a) < m.clave("spec_sens90", 0.90, 0.6, a)
    assert m.clave("spec_sens90", 0.89, 0.99, a) < m.clave("spec_sens90", 0.90, 0.1, a)


def test_cuenta_macro_y_mcnemar(m: ModuleType) -> None:
    us = [
        m.Unidad("x", "v1", True, "fall"),
        m.Unidad("x", "v2", True, "fall"),
        m.Unidad("x", "v3", False, "adl"),
        m.Unidad("x", "v4", False, "adl"),
    ]
    base, otro = bytes([1, 0, 1, 0]), bytes([1, 1, 0, 0])
    c = m.cuenta(us, otro, range(4))
    assert (c.vp, c.p, c.vn, c.n) == (2, 2, 2, 2)
    assert m.macro([c, m.cuenta(us, base, range(4))]) == pytest.approx((0.75, 0.75))
    b, cc, p = m.mcnemar(us, base, otro, range(4))
    assert (b, cc) == (0, 2)
    assert p == pytest.approx(0.5)
