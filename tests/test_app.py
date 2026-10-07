import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from detection_worker import __version__
from detection_worker.clasificacion.umbrales import Umbrales
from detection_worker.config import ConfiguracionInvalidaError, Settings, cargar_settings
from detection_worker.ingesta import protocolo
from detection_worker.main import Componentes, create_app
from tests import fabricas
from tests.conftest import TOKEN_INGESTA, AlmacenFalso, EstimadorFalso, PublicadorFalso


@pytest.fixture
def publicador() -> PublicadorFalso:
    return PublicadorFalso()


@pytest.fixture
def cliente(settings: Settings, publicador: PublicadorFalso) -> TestClient:
    componentes = Componentes(EstimadorFalso([fabricas.DE_PIE] * 5), publicador, AlmacenFalso())
    return TestClient(create_app(settings, componentes))


def test_health(cliente: TestClient) -> None:
    with cliente:
        respuesta = cliente.get("/health")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"estado": "ok", "version": __version__}


def test_ingesta_rechaza_token_invalido(cliente: TestClient) -> None:
    with (
        cliente,
        pytest.raises(WebSocketDisconnect) as error,
        cliente.websocket_connect(
            "/v1/ingesta/camara-1", headers={"Authorization": "Bearer otro"}
        ) as ws,
    ):
        ws.receive_bytes()
    assert error.value.code == 1008


def test_ingesta_acepta_fotogramas_con_token_valido(
    cliente: TestClient, publicador: PublicadorFalso
) -> None:
    with (
        cliente,
        cliente.websocket_connect(
            "/v1/ingesta/camara-1", headers={"Authorization": f"Bearer {TOKEN_INGESTA}"}
        ) as ws,
    ):
        for i in range(5):
            ws.send_bytes(protocolo.codificar(i * 100, b"\xff\xd8\xff\xe0contenido"))
        ws.send_bytes(b"mensaje-invalido")  # discarded without closing the connection
    assert publicador.eventos == []


def test_sin_calibrar_arranca_pero_rechaza_el_video(settings: Settings) -> None:
    sin_calibrar = settings.model_copy(update={"clasificacion": Umbrales()})
    componentes = Componentes(EstimadorFalso(), PublicadorFalso(), AlmacenFalso())
    cliente = TestClient(create_app(sin_calibrar, componentes))
    with cliente:
        assert cliente.get("/health").status_code == 200
        with (
            cliente.websocket_connect(
                "/v1/ingesta/camara-1", headers={"Authorization": f"Bearer {TOKEN_INGESTA}"}
            ) as ws,
            pytest.raises(WebSocketDisconnect) as error,
        ):
            ws.receive_bytes()
    assert error.value.code == 1011


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
