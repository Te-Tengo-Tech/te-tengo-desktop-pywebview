import contextlib
import json
import logging
import queue
import threading
from collections.abc import Iterator
from http import HTTPStatus
from typing import Any

import pytest
from websockets.datastructures import Headers
from websockets.exceptions import ConnectionClosed
from websockets.http11 import Request, Response
from websockets.sync.server import Server, ServerConnection, serve

from te_tengo_captura.backend.errores import SinConexionError
from te_tengo_captura.backend.modelos import ModoVista
from te_tengo_captura.backend.transmision import CanalTransmision, url_websocket

CLAVE = "clave-de-publicacion"
ORDEN = {
    "transmitir": True,
    "urlPublicacion": "rtsp://mediamtx:8554/camaras/camara-1",
    "usuario": "agente",
    "clave": CLAVE,
    "modo": "VIDEO",
}


class Tokens:
    """The camera token as ``ClienteBackend`` hands it out (``token_vigente``/``renovar_token``)."""

    def __init__(self) -> None:
        self.actual = "token-1"
        self.renovados: list[str] = []
        self.sin_conexion = False

    def token_vigente(self) -> str:
        if self.sin_conexion:
            raise SinConexionError("Sin conexión con el backend")
        return self.actual

    def renovar_token(self, rechazado: str) -> str:
        self.renovados.append(rechazado)
        self.actual = f"token-{len(self.renovados) + 1}"
        return self.actual


class Receptor:
    def __init__(self) -> None:
        self.llamadas: queue.Queue[tuple[Any, ...]] = queue.Queue()

    def transmitir(self, url: str, usuario: str | None, clave: str | None, modo: ModoVista) -> None:
        self.llamadas.put(("transmitir", url, usuario, clave, modo))

    def cambiar_modo(self, modo: ModoVista) -> None:
        self.llamadas.put(("modo", modo))

    def detener(self) -> None:
        self.llamadas.put(("detener",))

    def siguiente(self, ignorar_detener: bool = False) -> tuple[Any, ...]:
        while True:
            llamada = self.llamadas.get(timeout=5)
            if not (ignorar_detener and llamada == ("detener",)):
                return llamada


class ApiFalsa:
    """WebSocket server of ``/api/agente/transmision`` that accepts only ``token_valido``."""

    def __init__(self) -> None:
        self.token_valido = "token-1"
        self.conexiones: queue.Queue[ServerConnection] = queue.Queue()
        self.cabeceras: list[Headers] = []
        self.rutas: list[str] = []
        self.servidor: Server = serve(
            self._atender, "127.0.0.1", 0, process_request=self._autorizar
        )
        self.hilo = threading.Thread(target=self.servidor.serve_forever, daemon=True)
        self.hilo.start()

    @property
    def url(self) -> str:
        host, puerto = self.servidor.socket.getsockname()[:2]
        return f"http://{host}:{puerto}"

    def _autorizar(self, conexion: ServerConnection, solicitud: Request) -> Response | None:
        self.cabeceras.append(solicitud.headers)
        self.rutas.append(solicitud.path)
        if solicitud.headers.get("Authorization") != f"Bearer {self.token_valido}":
            return conexion.respond(HTTPStatus.UNAUTHORIZED, "SESION_EXPIRADA\n")
        return None

    def _atender(self, conexion: ServerConnection) -> None:
        self.conexiones.put(conexion)
        with contextlib.suppress(ConnectionClosed):
            for _ in conexion:  # the agent sends nothing; this waits until it closes
                pass

    def conexion(self) -> ServerConnection:
        return self.conexiones.get(timeout=5)

    def cerrar(self) -> None:
        self.servidor.shutdown()


@pytest.fixture
def api() -> Iterator[ApiFalsa]:
    servidor = ApiFalsa()
    yield servidor
    servidor.cerrar()


@pytest.fixture
def tokens() -> Tokens:
    return Tokens()


@pytest.fixture
def receptor() -> Receptor:
    return Receptor()


@pytest.fixture
def canal(api: ApiFalsa, tokens: Tokens, receptor: Receptor) -> Iterator[CanalTransmision]:
    canal = CanalTransmision(
        tokens, api.url, receptor, reintento_inicial_s=0.05, reintento_maximo_s=0.2
    )
    canal.iniciar()
    yield canal
    canal.detener()


@pytest.mark.parametrize(
    ("api_url", "esperada"),
    [
        ("http://localhost:8080", "ws://localhost:8080/api/agente/transmision"),
        ("https://api.tetengo.pe/", "wss://api.tetengo.pe/api/agente/transmision"),
        ("https://host/base", "wss://host/base/api/agente/transmision"),
    ],
)
def test_url_websocket(api_url: str, esperada: str) -> None:
    assert url_websocket(api_url) == esperada


def test_se_conecta_con_el_token_de_la_camara(api: ApiFalsa, canal: CanalTransmision) -> None:
    api.conexion()
    assert api.rutas == ["/api/agente/transmision"]
    assert api.cabeceras[0]["Authorization"] == "Bearer token-1"
    assert api.cabeceras[0]["Api-Version"] == "1"


def test_ordenes_de_la_api(api: ApiFalsa, canal: CanalTransmision, receptor: Receptor) -> None:
    conexion = api.conexion()
    conexion.send(json.dumps(ORDEN))
    assert receptor.siguiente() == (
        "transmitir",
        "rtsp://mediamtx:8554/camaras/camara-1",
        "agente",
        CLAVE,
        ModoVista.VIDEO,
    )
    conexion.send(json.dumps({"modo": "VIDEO_CON_POSTURA"}))
    assert receptor.siguiente() == ("modo", ModoVista.VIDEO_CON_POSTURA)
    conexion.send(json.dumps({"modo": "SOLO_POSTURA"}))
    assert receptor.siguiente() == ("modo", ModoVista.SOLO_POSTURA)
    conexion.send(json.dumps({"transmitir": False}))
    assert receptor.siguiente() == ("detener",)
    assert canal.conectado


def test_sin_modo_transmite_video(
    api: ApiFalsa, canal: CanalTransmision, receptor: Receptor
) -> None:
    conexion = api.conexion()
    conexion.send(json.dumps({key: v for key, v in ORDEN.items() if key != "modo"}))
    assert receptor.siguiente()[-1] is ModoVista.VIDEO


def test_mensajes_invalidos_se_ignoran_sin_mostrar_la_clave(
    api: ApiFalsa,
    canal: CanalTransmision,
    receptor: Receptor,
    caplog: pytest.LogCaptureFixture,
) -> None:
    conexion = api.conexion()
    with caplog.at_level(logging.INFO):
        conexion.send("no es json " + CLAVE)
        conexion.send(json.dumps({**ORDEN, "modo": "OTRO"}))
        conexion.send(json.dumps({"transmitir": True, "clave": CLAVE}))  # no URL
        conexion.send(b"\x00binario")
        conexion.send(json.dumps({}))
        conexion.send(json.dumps({"transmitir": False}))
        assert receptor.siguiente() == ("detener",)
    assert receptor.llamadas.empty()
    assert CLAVE not in caplog.text
    assert "mensaje inválido ignorado" in caplog.text
    assert "binario" in caplog.text


def test_con_401_se_registra_de_nuevo_y_reconecta(
    api: ApiFalsa, tokens: Tokens, receptor: Receptor
) -> None:
    api.token_valido = "token-2"  # the agent's token expired
    canal = CanalTransmision(tokens, api.url, receptor, reintento_inicial_s=0.05)
    canal.iniciar()
    try:
        api.conexion()
        assert tokens.renovados == ["token-1"]
        assert api.cabeceras[-1]["Authorization"] == "Bearer token-2"
    finally:
        canal.detener()


def test_si_se_cierra_la_conexion_detiene_la_vista_y_reconecta(
    api: ApiFalsa, canal: CanalTransmision, receptor: Receptor
) -> None:
    conexion = api.conexion()
    conexion.send(json.dumps(ORDEN))
    assert receptor.siguiente()[0] == "transmitir"
    conexion.close()
    assert receptor.siguiente() == ("detener",)  # no stream nobody can stop
    nueva = api.conexion()
    nueva.send(json.dumps(ORDEN))  # the API asks again if someone is still watching
    assert receptor.siguiente(ignorar_detener=True)[0] == "transmitir"


def test_sin_backend_reintenta(api: ApiFalsa, tokens: Tokens, receptor: Receptor) -> None:
    tokens.sin_conexion = True
    canal = CanalTransmision(tokens, api.url, receptor, reintento_inicial_s=0.05)
    assert canal.conectar_una_vez() == pytest.approx(0.05)
    assert canal.conectar_una_vez() == pytest.approx(0.1)
    tokens.sin_conexion = False
    canal.iniciar()
    try:
        api.conexion()
    finally:
        canal.detener()


def test_un_servidor_inexistente_espera_con_tope(tokens: Tokens, receptor: Receptor) -> None:
    canal = CanalTransmision(
        tokens, "http://127.0.0.1:9", receptor, reintento_inicial_s=1, reintento_maximo_s=4
    )
    esperas = [canal.conectar_una_vez() for _ in range(4)]
    assert esperas == [1, 2, 4, 4]


def test_401_repetido_espera(api: ApiFalsa, tokens: Tokens, receptor: Receptor) -> None:
    api.token_valido = "nunca"
    canal = CanalTransmision(tokens, api.url, receptor, reintento_inicial_s=1)
    assert canal.conectar_una_vez() == 0  # renewed: try again at once
    assert canal.conectar_una_vez() == 2  # still rejected: back off
    assert tokens.renovados == ["token-1", "token-2"]


def test_detener_cierra_la_conexion_abierta(
    api: ApiFalsa, tokens: Tokens, receptor: Receptor
) -> None:
    canal = CanalTransmision(tokens, api.url, receptor)
    canal.iniciar()
    api.conexion()
    canal.detener(espera_s=5)
    assert not canal._hilo.is_alive()
    assert not canal.conectado
