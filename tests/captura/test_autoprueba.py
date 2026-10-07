import sys
from pathlib import Path

import pytest

from te_tengo_captura import autoprueba

MODELO = Path("models/pose_landmarker_lite.task")


@pytest.mark.integracion
@pytest.mark.skipif(not MODELO.is_file(), reason="Falta el modelo: ejecuta `make modelo`")
def test_autoprueba_completa(monkeypatch: pytest.MonkeyPatch) -> None:
    # pystray needs a display on Linux; the packaged Windows build imports the real one.
    monkeypatch.setitem(sys.modules, "pystray", type(sys)("pystray"))
    assert autoprueba.ejecutar(MODELO) == 0


def test_autoprueba_sin_modelo_falla(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    assert autoprueba.ejecutar(tmp_path / "no.task") == 1
    assert "Autoprueba: modelo de pose FALLÓ" in caplog.text


def test_autoprueba_detecta_assets_faltantes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    from te_tengo_captura.ui import ventana

    monkeypatch.setattr(ventana, "WEB", tmp_path)
    monkeypatch.setitem(sys.modules, "pystray", type(sys)("pystray"))
    monkeypatch.setitem(sys.modules, "webview", type(sys)("webview"))
    autoprueba.ejecutar(tmp_path / "no.task")
    assert "Autoprueba: interfaz FALLÓ" in caplog.text
