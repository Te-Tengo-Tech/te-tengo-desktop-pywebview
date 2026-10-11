import threading

import pytest

from te_tengo_captura.backend.errores import PcDesvinculadaError, SinConexionError
from te_tengo_captura.backend.falso import URL_API, BackendFalso
from te_tengo_captura.vinculacion.credenciales import AlmacenCredenciales, LlaveroEnMemoria
from te_tengo_captura.vinculacion.oauth import ClienteOAuth
from te_tengo_captura.vinculacion.sesion import MARGEN_S, SesionPc, credenciales_de


class Reloj:
    def __init__(self) -> None:
        self.ahora = 1_000_000.0

    def __call__(self) -> float:
        return self.ahora


class Escenario:
    def __init__(self) -> None:
        self.falso = BackendFalso()
        self.oauth = ClienteOAuth(URL_API, self.falso.transporte())
        self.almacen = AlmacenCredenciales(LlaveroEnMemoria())
        self.reloj = Reloj()
        codigo = self.oauth.pedir_codigo("PC", "x", "y")
        self.falso.aprobar()
        credenciales = credenciales_de(self.oauth.canjear(codigo.device_code), self.reloj())
        self.almacen.guardar(credenciales)
        self.desvinculaciones: list[str] = []
        self.sesion = SesionPc(
            self.oauth, self.almacen, credenciales, self.desvinculaciones.append, self.reloj
        )


@pytest.fixture
def e() -> Escenario:
    return Escenario()


def test_usa_el_token_vigente_y_renueva_antes_de_que_venza(e: Escenario) -> None:
    primero = e.sesion.token_vigente()
    assert e.sesion.token_vigente() == primero
    renovacion = e.sesion.refresh_token()
    e.reloj.ahora += 3600 - MARGEN_S + 1
    segundo = e.sesion.token_vigente()
    assert segundo != primero
    guardadas = e.almacen.leer()
    assert guardadas is not None
    # The new refresh token replaced the old one in the OS store in the same step.
    assert guardadas.refresh_token == e.sesion.refresh_token() != renovacion
    assert guardadas.access_token == segundo


def test_tras_un_401_renueva_una_sola_vez(e: Escenario) -> None:
    llamadas: list[str] = []
    e.sesion.al_renovar.append(lambda: llamadas.append("camaras"))
    rechazado = e.sesion.token_vigente()
    nuevo = e.sesion.renovar_token(rechazado)
    assert nuevo != rechazado
    # Another thread got the same 401 with the old token: no second renewal.
    assert e.sesion.renovar_token(rechazado) == nuevo
    assert llamadas == ["camaras"]


def test_renovaciones_en_paralelo_presentan_cada_token_una_vez(e: Escenario) -> None:
    e.reloj.ahora += 3600
    errores: list[BaseException] = []

    def usar() -> None:
        try:
            e.sesion.token_vigente()
        except BaseException as error:
            errores.append(error)

    hilos = [threading.Thread(target=usar) for _ in range(8)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()
    assert errores == []
    assert not e.falso.pc_quitada  # no refresh token was reused


def test_sin_conexion_el_mismo_token_se_reintenta(e: Escenario) -> None:
    e.reloj.ahora += 3600
    renovacion = e.sesion.refresh_token()
    e.falso.sin_conexion = True
    with pytest.raises(SinConexionError):
        e.sesion.token_vigente()
    assert e.sesion.refresh_token() == renovacion
    e.falso.sin_conexion = False
    assert e.sesion.token_vigente()


def test_quitada_desde_la_app_desvincula_una_vez(e: Escenario) -> None:
    e.falso.quitar_pc()
    e.reloj.ahora += 3600
    with pytest.raises(PcDesvinculadaError):
        e.sesion.token_vigente()
    with pytest.raises(PcDesvinculadaError):
        e.sesion.token_vigente()
    assert e.desvinculaciones == ["invalid_grant"]
    assert e.sesion.desvinculada


def test_los_secretos_para_el_filtro_del_registro(e: Escenario) -> None:
    secretos = e.sesion.secretos()
    assert e.sesion.token_vigente() in secretos
    assert e.sesion.refresh_token() in secretos
