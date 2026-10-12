from urllib.parse import parse_qs

import httpx
import pytest

from te_tengo_captura.backend.errores import ErrorBackendError, SinConexionError
from te_tengo_captura.backend.falso import URL_API, BackendFalso
from te_tengo_captura.vinculacion.oauth import ClienteOAuth, RechazoOAuthError


def formulario(solicitud: httpx.Request) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(solicitud.content.decode()).items()}


def test_pide_el_codigo_con_un_formulario_y_sin_token() -> None:
    falso = BackendFalso()
    oauth = ClienteOAuth(URL_API, falso.transporte())
    codigo = oauth.pedir_codigo("Sala-Rosa", "Windows 11 Home", "0.5.0")
    solicitud = falso.solicitudes[-1]
    assert solicitud.url.path == "/api/agente/vinculacion"
    assert solicitud.headers["Content-Type"] == "application/x-www-form-urlencoded"
    assert "Authorization" not in solicitud.headers
    assert solicitud.headers["Api-Version"] == "1"
    assert formulario(solicitud) == {
        "client_id": "te-tengo-captura",
        "nombre_pc": "Sala-Rosa",
        "sistema_operativo": "Windows 11 Home",
        "version_agente": "0.5.0",
    }
    assert len(codigo.user_code) == 9
    assert codigo.user_code[4] == "-"
    assert codigo.verification_uri_complete.endswith(codigo.user_code)
    assert (codigo.expires_in, codigo.interval) == (600, 5)
    assert codigo.device_code not in repr(codigo)  # the secret never shows


def test_sondeo_pendiente_aprobado_y_rotacion() -> None:
    falso = BackendFalso()
    oauth = ClienteOAuth(URL_API, falso.transporte())
    codigo = oauth.pedir_codigo("Sala-Rosa", "macOS 15.4", "0.5.0")
    with pytest.raises(RechazoOAuthError) as pendiente:
        oauth.canjear(codigo.device_code)
    assert pendiente.value.codigo == "authorization_pending"
    assert formulario(falso.solicitudes[-1]) == {
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        "device_code": codigo.device_code,
        "client_id": "te-tengo-captura",
    }
    falso.aprobar()
    tokens = oauth.canjear(codigo.device_code)
    assert (tokens.pc_id, tokens.hogar_id, tokens.expires_in) == ("pc-1", "hogar-1", 3600)
    assert tokens.access_token not in repr(tokens)
    assert tokens.refresh_token not in repr(tokens)
    with pytest.raises(RechazoOAuthError) as usado:  # the device code works once
        oauth.canjear(codigo.device_code)
    assert usado.value.codigo == "invalid_grant"
    nuevos = oauth.renovar(tokens.refresh_token)
    assert nuevos.refresh_token != tokens.refresh_token
    assert formulario(falso.solicitudes[-1])["grant_type"] == "refresh_token"
    with pytest.raises(RechazoOAuthError) as reuso:  # RFC 9700: reuse unlinks the PC
        oauth.renovar(tokens.refresh_token)
    assert reuso.value.codigo == "invalid_grant"
    assert falso.pc_quitada


@pytest.mark.parametrize("borrar", [False, True])
def test_revocar_el_token_de_renovacion(borrar: bool) -> None:
    falso = BackendFalso()
    oauth = ClienteOAuth(URL_API, falso.transporte())
    codigo = oauth.pedir_codigo("PC", "x", "y")
    falso.aprobar()
    tokens = oauth.canjear(codigo.device_code)
    oauth.revocar(tokens.refresh_token, datos_locales_borrados=borrar)
    campos = formulario(falso.solicitudes[-1])
    assert campos["token"] == tokens.refresh_token
    assert campos["token_type_hint"] == "refresh_token"
    assert ("datos_locales_borrados" in campos) is borrar
    assert falso.pc_quitada


def test_errores_de_red_y_del_servidor() -> None:
    falso = BackendFalso()
    oauth = ClienteOAuth(URL_API, falso.transporte())
    falso.sin_conexion = True
    with pytest.raises(SinConexionError):
        oauth.pedir_codigo("PC", "x", "y")
    falso.sin_conexion = False
    falso.fallos.append(503)
    with pytest.raises(ErrorBackendError) as servidor:
        oauth.pedir_codigo("PC", "x", "y")
    assert not isinstance(servidor.value, RechazoOAuthError)
    assert servidor.value.reintentable


def test_cliente_desconocido() -> None:
    def responder(solicitud: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid_client"})

    oauth = ClienteOAuth(URL_API, httpx.MockTransport(responder))
    with pytest.raises(RechazoOAuthError) as error:
        oauth.pedir_codigo("PC", "x", "y")
    assert (error.value.codigo, error.value.estado) == ("invalid_client", 401)
