"""The detection core stays pure: no app, GUI or network imports (AGENTS.md, ADR 0007)."""

import ast
from pathlib import Path

import te_tengo_deteccion

PROHIBIDOS = ("te_tengo_captura", "webview", "pystray", "httpx")
RAIZ = Path(te_tengo_deteccion.__file__).parent


def _modulos_importados(archivo: Path) -> set[str]:
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    modulos: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos.update(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
            modulos.add(nodo.module)
    return modulos


def test_el_nucleo_de_deteccion_no_importa_la_app_ni_la_red() -> None:
    archivos = sorted(RAIZ.rglob("*.py"))
    assert archivos
    violaciones = [
        f"{archivo.relative_to(RAIZ)}: {modulo}"
        for archivo in archivos
        for modulo in _modulos_importados(archivo)
        if modulo.split(".")[0] in PROHIBIDOS
    ]
    assert violaciones == []


def test_la_deteccion_de_importaciones_funciona(tmp_path: Path) -> None:
    archivo = tmp_path / "x.py"
    archivo.write_text("import httpx\nfrom te_tengo_captura.estado import X\n", encoding="utf-8")
    assert _modulos_importados(archivo) == {"httpx", "te_tengo_captura.estado"}
