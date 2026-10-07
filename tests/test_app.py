import pytest

from detection_worker.config import ConfiguracionInvalidaError, Settings, cargar_settings


def test_variable_vacia_cuenta_como_no_definida(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TT_CLASIFICACION__VELOCIDAD_DESCENSO_MIN", "")
    config = Settings(
        _env_file=None,
        ingesta_token="t",
        backend_url="http://backend.test",
        backend_token="b",
        clips_bucket="c",
    )
    assert not config.clasificacion.calibrado


def test_configuracion_incompleta_explica_que_falta(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir("/")  # no .env
    for variable in ("TT_INGESTA_TOKEN", "TT_BACKEND_TOKEN", "TT_BACKEND_URL", "TT_CLIPS_BUCKET"):
        monkeypatch.delenv(variable, raising=False)
    with pytest.raises(ConfiguracionInvalidaError, match="TT_INGESTA_TOKEN"):
        cargar_settings()
