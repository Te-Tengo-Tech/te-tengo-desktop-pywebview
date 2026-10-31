"""The nested candidate evaluation (``scripts/evaluar_candidatos.py``): statistics and nesting."""

import importlib
from pathlib import Path
from types import ModuleType

import pytest

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture
def modulo(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.syspath_prepend(str(RAIZ / "scripts"))
    return importlib.import_module("evaluar_candidatos")


def test_mcnemar_exacto(modulo: ModuleType) -> None:
    assert modulo.mcnemar_exacto(0, 0) == 1.0
    assert modulo.mcnemar_exacto(0, 2) == pytest.approx(0.5)
    # 10 vs 2 discordant pairs: 2 * P(X <= 2), X ~ Bin(12, 0.5) = 2 * 79 / 4096.
    assert modulo.mcnemar_exacto(10, 2) == pytest.approx(158 / 4096)
    assert modulo.mcnemar_exacto(2, 10) == modulo.mcnemar_exacto(10, 2)


def _video(modulo: ModuleType, nombre: str, grupo: str, es_caida: bool) -> object:
    return modulo.Video("caucafall", nombre, Path(nombre), es_caida, "x", grupo)


def test_el_umbral_se_elige_sin_el_grupo_de_prueba(modulo: ModuleType) -> None:
    """Group A prefers v = 0.2 and group B v = 0.1: each fold must take the other's value."""
    videos = [
        _video(modulo, "a-caida", "A", True),
        _video(modulo, "a-adl", "A", False),
        _video(modulo, "b-caida", "B", True),
        _video(modulo, "b-adl", "B", False),
    ]
    caida = [("caida", 1.0)]
    bajo = (("velocidad_descenso_min", 0.1),)
    alto = (("velocidad_descenso_min", 0.2),)
    corridas = {
        bajo: {"a-caida": caida, "a-adl": caida, "b-caida": caida, "b-adl": []},
        alto: {"a-caida": caida, "a-adl": [], "b-caida": [], "b-adl": []},
    }
    rejillas: dict[object, dict[str, list[object]]] = {bajo: {}, alto: {}}
    r = modulo.evaluar_candidato("x", [bajo, alto], corridas, rejillas, videos)
    assert r.elegidos == {"A": bajo, "B": alto}
    assert r.salida == {"a-caida": True, "a-adl": True, "b-caida": False, "b-adl": False}


def test_empate_elige_la_velocidad_menor_y_el_valor_mas_conservador(modulo: ModuleType) -> None:
    rejilla = {"velocidad_perdida_min": [0.1, 0.5, 1.0]}
    a = (("velocidad_descenso_min", 0.01), ("velocidad_perdida_min", 0.1))
    b = (("velocidad_descenso_min", 0.01), ("velocidad_perdida_min", 1.0))
    c = (("velocidad_descenso_min", 0.05), ("velocidad_perdida_min", 1.0))
    assert max([a, b, c], key=lambda x: modulo.clave_desempate(x, rejilla)) == b


def test_angulo_y_razon_publicados_ganan_los_empates(modulo: ModuleType) -> None:
    assert modulo.ANGULOS[-1] == 45.0
    assert modulo.RAZONES[-1] == 1.0
