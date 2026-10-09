import pytest


@pytest.fixture(autouse=True)
def bandeja_sin_appkit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests drive the fake pystray directly; on macOS the real tray defers to the AppKit loop."""
    monkeypatch.setattr("te_tengo_captura.bandeja.icono.EN_MACOS", False)
