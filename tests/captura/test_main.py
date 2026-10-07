from pathlib import Path

import pytest

from te_tengo_captura import __version__
from te_tengo_captura.__main__ import main


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as salida:
        main(["--version"])
    assert salida.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_configuracion_invalida_explica_el_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--config", str(tmp_path / "no-existe.toml")]) == 2
    assert "No se encontró el archivo de configuración" in capsys.readouterr().err


def test_arranca_con_el_ejemplo() -> None:
    assert main(["--config", str(Path(__file__).resolve().parents[2] / "config.ejemplo.toml")]) == 0
