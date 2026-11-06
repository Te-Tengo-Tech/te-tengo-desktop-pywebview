"""Grids, tie-breaks and censoring of scripts/evaluar_especificidad.py (ADR 0012)."""

import importlib
from pathlib import Path
from types import ModuleType

import pytest

from te_tengo_deteccion.clasificacion.umbrales import Umbrales
from tests import fabricas

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture
def m(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.syspath_prepend(str(RAIZ / "scripts"))
    return importlib.import_module("evaluar_especificidad")


def test_rejillas_registradas(m: ModuleType) -> None:
    tamanos = {n: len(m.ajustes_de(n)) for n in m.TODAS}
    assert tamanos["base"] == 100
    assert tamanos["S1"] == 1200
    assert tamanos["S2 (F3)"] == 500
    assert tamanos["S3"] == tamanos["S4"] == 100
    assert tamanos["S1+F3"] == 6000


def test_desempate_prefiere_lo_mas_cercano_a_lo_desplegado(m: ModuleType) -> None:
    ajustes = m.ajustes_de("S1")
    mejor = max(ajustes, key=lambda a: m.desempate("S1", a))
    assert dict(mejor) == {
        "velocidad_descenso_min": 0.01,
        "retencion_caida_s": 2.0,
        "retencion_erguido_s": 1.0,
        "retencion_exige_visibles": True,
    }


def test_retencion_abierta_al_final_del_clip_cuenta_como_caida(m: ModuleType) -> None:
    secuencia = [(round(0.1 * i, 1), fabricas.DE_PIE) for i in range(11)]
    secuencia += [(1.1, fabricas.CAYENDO), (1.2, fabricas.TENDIDA)]
    u = Umbrales(velocidad_descenso_min=0.5, retencion_caida_s=5.0)
    eventos = m.replay(secuencia, u)
    assert eventos == [(m.CAIDA, 1.2), (m.CENSURADA, 1.2)]
    assert m.detecto(eventos)
    assert m.replay(secuencia, Umbrales(velocidad_descenso_min=0.5)) == [(m.CAIDA, 1.1)]
