import sys
from typing import Any

import pytest

from te_tengo_captura import autoinicio


class RegistroFalso:
    HKEY_CURRENT_USER = "HKCU"
    KEY_ALL_ACCESS = 0xF003F
    REG_SZ = 1

    def __init__(self, valores: dict[str, str] | None = None, error: OSError | None = None) -> None:
        self.valores = dict(valores or {})
        self.escrituras: list[tuple[str, str]] = []
        self.error = error
        self.abierta: tuple[Any, ...] | None = None

    def OpenKey(self, raiz: str, ruta: str, reservado: int, acceso: int) -> "RegistroFalso":  # noqa: N802
        if self.error:
            raise self.error
        self.abierta = (raiz, ruta, acceso)
        return self

    def __enter__(self) -> "RegistroFalso":
        return self

    def __exit__(self, *args: object) -> None:
        pass

    def QueryValueEx(self, clave: object, nombre: str) -> tuple[str, int]:  # noqa: N802
        if nombre not in self.valores:
            raise FileNotFoundError(nombre)
        return self.valores[nombre], self.REG_SZ

    def SetValueEx(self, clave: object, nombre: str, reservado: int, tipo: int, valor: str) -> None:  # noqa: N802
        self.valores[nombre] = valor
        self.escrituras.append((nombre, valor))


@pytest.fixture
def empaquetado(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Program Files\TeTengoCaptura\te-tengo-captura.exe")
    return r'"C:\Program Files\TeTengoCaptura\te-tengo-captura.exe"'


def test_registra_la_entrada_run_del_usuario(empaquetado: str) -> None:
    registro = RegistroFalso()
    assert autoinicio.registrar(registro, "win32")
    assert registro.abierta == ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Run", 0xF003F)
    assert registro.escrituras == [("TeTengoCaptura", empaquetado)]


def test_no_reescribe_si_ya_esta(empaquetado: str) -> None:
    registro = RegistroFalso({"TeTengoCaptura": empaquetado})
    assert autoinicio.registrar(registro, "win32")
    assert registro.escrituras == []


def test_actualiza_si_el_programa_se_movio(empaquetado: str) -> None:
    registro = RegistroFalso({"TeTengoCaptura": r'"D:\viejo.exe"'})
    autoinicio.registrar(registro, "win32")
    assert registro.valores["TeTengoCaptura"] == empaquetado


def test_error_del_registro(empaquetado: str) -> None:
    assert not autoinicio.registrar(RegistroFalso(error=PermissionError("denegado")), "win32")


def test_no_hace_nada_fuera_de_windows_ni_desde_el_codigo_fuente(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registro = RegistroFalso()
    assert not autoinicio.registrar(registro, "linux")
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    assert autoinicio.comando() is None
    assert not autoinicio.registrar(registro, "win32")
    assert registro.escrituras == []
