import pytest


@pytest.fixture(autouse=True)
def bandeja_sin_appkit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests drive the fake pystray directly; on macOS the real tray defers to the AppKit loop."""
    monkeypatch.setattr("te_tengo_captura.bandeja.icono.EN_MACOS", False)


@pytest.fixture(autouse=True)
def sin_llavero_del_sistema(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test may read or write the real OS credential store: each one gets its own memory."""
    from te_tengo_captura.vinculacion.credenciales import LlaveroEnMemoria

    llavero = LlaveroEnMemoria()
    monkeypatch.setattr("te_tengo_captura.almacen.cifrado.almacen_del_sistema", lambda: llavero)
    monkeypatch.setattr(
        "te_tengo_captura.vinculacion.credenciales.llavero_del_sistema", lambda: llavero
    )
