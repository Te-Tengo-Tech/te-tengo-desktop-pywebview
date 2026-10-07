from pathlib import Path

import pytest

from te_tengo_captura import __version__
from te_tengo_captura.__main__ import argumentos, construir_agente, main
from te_tengo_captura.captura.fuentes import FuenteArchivo
from te_tengo_captura.config import Configuracion

MODELO = Path("models/pose_landmarker_lite.task")


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as salida:
        main(["--version"])
    assert salida.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_configuracion_invalida_explica_el_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--config", str(tmp_path / "no-existe.toml"), "--datos", str(tmp_path)]) == 2
    assert "No se encontró el archivo de configuración" in capsys.readouterr().err


def test_falta_el_modelo(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], configuracion: Configuracion
) -> None:
    ejemplo = Path(__file__).resolve().parents[2] / "config.ejemplo.toml"
    codigo = main(
        ["--config", str(ejemplo), "--modelo", str(tmp_path / "no.task"), "--datos", str(tmp_path)]
    )
    assert codigo == 2
    assert "make modelo" in capsys.readouterr().err


@pytest.mark.skipif(not MODELO.is_file(), reason="Falta el modelo: ejecuta `make modelo`")
def test_construye_el_agente_con_backend_falso_y_video(
    tmp_path: Path, configuracion: Configuracion
) -> None:
    args = argumentos(
        ["--backend-falso", "--video", str(tmp_path / "demo.mp4"), "--datos", str(tmp_path)]
    )
    agente = construir_agente(args, configuracion)
    assert isinstance(agente.captador._fuente, FuenteArchivo)
    assert agente.reintentar_ahora()  # the fake backend answers the heartbeat
    assert agente.estado().situacion.value == "enviando"
    agente.detener()


def test_segundo_lanzamiento_avisa_y_sale(tmp_path: Path) -> None:
    import threading

    from te_tengo_captura.instancia import Instancia

    mostrada = threading.Event()
    primera = Instancia(tmp_path)
    assert primera.adquirir(mostrada.set)
    assert main(["--datos", str(tmp_path)]) == 0
    assert mostrada.wait(5)
    primera.liberar()


@pytest.mark.skipif(not MODELO.is_file(), reason="Falta el modelo: ejecuta `make modelo`")
def test_main_ejecuta_la_aplicacion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import te_tengo_captura.__main__ as principal

    ejecutadas: list[object] = []
    monkeypatch.setattr(
        principal, "ejecutar_aplicacion", lambda agente, abrir: ejecutadas.append(agente)
    )
    ejemplo = Path(__file__).resolve().parents[2] / "config.ejemplo.toml"
    assert main(["--config", str(ejemplo), "--backend-falso", "--datos", str(tmp_path)]) == 0
    assert len(ejecutadas) == 1
