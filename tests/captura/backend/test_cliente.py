import logging
from datetime import UTC, datetime

import httpx
import pytest

from te_tengo_captura.backend.cliente import ClienteBackend
from te_tengo_captura.backend.errores import (
    CapturaNoPermitidaError,
    CredencialInvalidaError,
    ErrorBackendError,
    EventoNoEncontradoError,
    NoAutorizadoError,
    SinConexionError,
)
from te_tengo_captura.backend.falso import URL_API, BackendFalso
from te_tengo_captura.backend.modelos import EventoAgente, MotivoCaptura
from te_tengo_deteccion.clasificacion.estados import TipoEvento

CREDENCIAL = "credencial-secreta"


@pytest.fixture
def backend() -> BackendFalso:
    return BackendFalso(credencial=CREDENCIAL)


@pytest.fixture
def cliente(backend: BackendFalso) -> ClienteBackend:
    return ClienteBackend(URL_API, CREDENCIAL, "Sala", "1.0.0", transporte=backend.transporte())


def evento(evento_id: str = "0192f6e4-0000-7000-8000-000000000001") -> EventoAgente:
    return EventoAgente(
        evento_id=evento_id,
        tipo=TipoEvento.CAIDA,
        ocurrido_en=datetime(2026, 10, 7, 15, 4, 31, 250000, tzinfo=UTC),
        parametros={"angulo_grados": 22.1, "razon_ancho_alto": 1.8, "velocidad": 0.41},
    )


def test_registro_envia_credencial_habitacion_y_version(
    backend: BackendFalso, cliente: ClienteBackend
) -> None:
    registro = cliente.registrar()
    assert (registro.camara_id, registro.hogar_id) == ("camara-1", "hogar-1")
    assert registro.nombre_habitacion == "Sala"
    solicitud = backend.solicitudes[-1]
    assert solicitud.method == "POST"
    assert solicitud.url.path == "/api/agente/camaras/registro"
    assert solicitud.headers["Api-Version"] == "1"
    assert "Authorization" not in solicitud.headers
    assert solicitud.read() == (
        b'{"credencialInstalacion":"credencial-secreta","nombreHabitacion":"Sala",'
        b'"versionAgente":"1.0.0"}'
    )


def test_registro_devuelve_el_nombre_guardado_en_el_backend(
    backend: BackendFalso, cliente: ClienteBackend
) -> None:
    backend.nombre_habitacion = "Dormitorio"  # renamed in the app (CA-06.2)
    assert cliente.registrar().nombre_habitacion == "Dormitorio"


def test_credencial_invalida(backend: BackendFalso) -> None:
    cliente = ClienteBackend(URL_API, "otra", "Sala", "1.0.0", transporte=backend.transporte())
    with pytest.raises(CredencialInvalidaError) as error:
        cliente.estado_captura()
    assert (error.value.estado, error.value.codigo) == (401, "CREDENCIAL_INVALIDA")
    assert not error.value.reintentable


def test_registra_antes_de_la_primera_llamada_y_usa_el_token(
    backend: BackendFalso, cliente: ClienteBackend
) -> None:
    estado = cliente.estado_captura()
    assert estado.captura_permitida
    assert backend.registros == 1
    solicitud = backend.solicitudes[-1]
    assert (solicitud.method, solicitud.url.path) == ("GET", "/api/agente/estado-captura")
    assert solicitud.headers["Authorization"] == "Bearer token-1"
    assert solicitud.headers["Api-Version"] == "1"


def test_401_vuelve_a_registrar_y_reintenta(backend: BackendFalso, cliente: ClienteBackend) -> None:
    cliente.estado_captura()
    backend.expirar_tokens()
    assert cliente.estado_captura().captura_permitida
    assert backend.registros == 2
    assert backend.solicitudes[-1].headers["Authorization"] == "Bearer token-2"


def test_401_persistente_falla(backend: BackendFalso, cliente: ClienteBackend) -> None:
    cliente.registrar()
    backend.fallos = [401, 401]
    with pytest.raises((NoAutorizadoError, ErrorBackendError)):
        cliente.estado_captura()


def test_estado_captura_en_pausa(backend: BackendFalso, cliente: ClienteBackend) -> None:
    hasta = datetime(2026, 10, 7, 20, 0, tzinfo=UTC)
    backend.pausar(hasta)
    estado = cliente.estado_captura()
    assert not estado.captura_permitida
    assert estado.motivo is MotivoCaptura.EN_PAUSA
    assert estado.pausada_hasta == hasta
    assert estado.nombre_habitacion == "Sala"


def test_senal_envia_el_cuerpo_y_devuelve_el_estado(
    backend: BackendFalso, cliente: ClienteBackend
) -> None:
    backend.quitar_consentimiento()
    estado = cliente.senal(webcam_conectada=False, deteccion_confiable=True)
    assert estado.motivo is MotivoCaptura.SIN_CONSENTIMIENTO
    assert backend.senales == [
        {"webcamConectada": False, "deteccionConfiable": True, "versionAgente": "1.0.0"}
    ]


def test_publicar_evento_y_reenvio_idempotente(
    backend: BackendFalso, cliente: ClienteBackend
) -> None:
    recibido, duplicado = cliente.publicar_evento(evento())
    assert (recibido.evento_id, duplicado) == (evento().evento_id, False)
    assert backend.eventos[evento().evento_id] == {
        "eventoId": "0192f6e4-0000-7000-8000-000000000001",
        "tipo": "caida",
        "ocurridoEn": "2026-10-07T15:04:31.250Z",
        "parametros": {"angulo_grados": 22.1, "razon_ancho_alto": 1.8, "velocidad": 0.41},
    }
    _, duplicado = cliente.publicar_evento(evento())
    assert duplicado
    assert len(backend.eventos) == 1


def test_evento_con_captura_no_permitida(backend: BackendFalso, cliente: ClienteBackend) -> None:
    backend.quitar_consentimiento()
    with pytest.raises(CapturaNoPermitidaError) as error:
        cliente.publicar_evento(evento())
    assert error.value.estado == 409
    assert not error.value.reintentable


def test_subida_de_clip(backend: BackendFalso, cliente: ClienteBackend) -> None:
    cliente.publicar_evento(evento())
    subida = cliente.solicitar_subida_clip(evento().evento_id, 4)
    solicitud = backend.solicitudes[-1]
    assert solicitud.url.path == f"/api/agente/eventos/{evento().evento_id}/clip"
    assert solicitud.read() == b'{"contentType":"video/mp4","tamanoBytes":4}'
    cliente.subir_clip(subida, b"mp4!")
    put = backend.solicitudes[-1]
    assert put.method == "PUT"
    assert "Authorization" not in put.headers
    assert "Api-Version" not in put.headers
    assert backend.clips[evento().evento_id].contenido == b"mp4!"
    assert backend.clips[evento().evento_id].content_type == "video/mp4"


def test_clip_de_evento_inexistente(cliente: ClienteBackend) -> None:
    with pytest.raises(EventoNoEncontradoError):
        cliente.solicitar_subida_clip("no-existe", 10)


def test_subida_rechazada_por_el_almacenamiento(
    backend: BackendFalso, cliente: ClienteBackend
) -> None:
    cliente.publicar_evento(evento())
    subida = cliente.solicitar_subida_clip(evento().evento_id, 4)
    cliente.subir_clip(subida, b"mp4!")
    with pytest.raises(ErrorBackendError) as error:
        cliente.subir_clip(subida, b"mp4!")  # the URL was already used
    assert error.value.estado == 403


def test_configuracion_remota(backend: BackendFalso, cliente: ClienteBackend) -> None:
    backend.umbrales = {"confirmacion_suelo_s": 20}
    remota = cliente.configuracion()
    assert remota.version_agente == "1.0.0"
    assert remota.umbrales == {"confirmacion_suelo_s": 20}


def test_sin_conexion_es_reintentable(backend: BackendFalso, cliente: ClienteBackend) -> None:
    backend.sin_conexion = True
    with pytest.raises(SinConexionError) as error:
        cliente.estado_captura()
    assert error.value.reintentable


def test_subida_sin_conexion(backend: BackendFalso, cliente: ClienteBackend) -> None:
    cliente.publicar_evento(evento())
    subida = cliente.solicitar_subida_clip(evento().evento_id, 4)
    backend.sin_conexion = True
    with pytest.raises(SinConexionError):
        cliente.subir_clip(subida, b"mp4!")


@pytest.mark.parametrize(("estado", "reintentable"), [(503, True), (429, True), (400, False)])
def test_errores_del_servidor(
    backend: BackendFalso, cliente: ClienteBackend, estado: int, reintentable: bool
) -> None:
    cliente.registrar()
    backend.fallos = [estado]
    with pytest.raises(ErrorBackendError) as error:
        cliente.estado_captura()
    assert error.value.estado == estado
    assert error.value.codigo == "FALLO_SIMULADO"
    assert error.value.reintentable is reintentable


def test_respuesta_que_no_es_problem_detail() -> None:
    transporte = httpx.MockTransport(lambda _: httpx.Response(500, text="<html>"))
    cliente = ClienteBackend(URL_API, CREDENCIAL, "Sala", "1.0.0", transporte=transporte)
    with pytest.raises(ErrorBackendError) as error:
        cliente.registrar()
    assert (error.value.estado, error.value.codigo) == (500, None)


def test_respuesta_con_cuerpo_inesperado() -> None:
    transporte = httpx.MockTransport(lambda _: httpx.Response(200, json={"otra": "cosa"}))
    cliente = ClienteBackend(URL_API, CREDENCIAL, "Sala", "1.0.0", transporte=transporte)
    with pytest.raises(ErrorBackendError, match="Respuesta inesperada"):
        cliente.registrar()


def test_no_registra_secretos_en_los_logs(
    backend: BackendFalso, cliente: ClienteBackend, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    cliente.publicar_evento(evento())
    backend.expirar_tokens()
    subida = cliente.solicitar_subida_clip(evento().evento_id, 4)
    cliente.subir_clip(subida, b"mp4!")
    backend.sin_conexion = True
    with pytest.raises(SinConexionError) as error:
        cliente.senal(True, True)
    texto = caplog.text + str(error.value)
    assert CREDENCIAL not in texto
    assert "token-" not in texto
    assert "firma=secreta" not in texto
    cliente.cerrar()


def test_secretos_para_el_filtro_de_logs(cliente: ClienteBackend) -> None:
    assert cliente.secretos() == [CREDENCIAL]
    cliente.registrar()
    assert cliente.secretos() == [CREDENCIAL, "token-1"]


def test_evento_omite_parametros_no_finitos() -> None:
    evento = EventoAgente(
        evento_id="0192f6e4-0000-7000-8000-000000000000",
        tipo=TipoEvento.CAIDA,
        ocurrido_en=datetime(2026, 10, 7, 15, 4, 31, tzinfo=UTC),
        parametros={"angulo_grados": 22.1, "razon_ancho_alto": float("inf")},
    )

    cuerpo = evento.json_api()

    assert cuerpo["parametros"] == {"angulo_grados": 22.1}
    httpx.Request("POST", "http://api", json=cuerpo)  # serializable without NaN or infinity


def test_hilos_concurrentes_registran_una_sola_vez(
    backend: BackendFalso, cliente: ClienteBackend
) -> None:
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=4) as hilos:
        estados = list(hilos.map(lambda _: cliente.estado_captura(), range(8)))

    assert all(estado.captura_permitida for estado in estados)
    assert backend.registros == 1
