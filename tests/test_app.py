import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from detection_worker import __version__
from detection_worker.config import Settings
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
        ws.send_bytes(b"mensaje-invalido")  # se descarta sin cerrar la conexión
    assert publicador.eventos == []
