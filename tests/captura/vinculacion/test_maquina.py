import logging

import pytest

from te_tengo_captura.backend.falso import URL_API, BackendFalso
from te_tengo_captura.vinculacion.maquina import REINTENTO_S, Fase, Vinculador
from te_tengo_captura.vinculacion.oauth import ClienteOAuth, TokensPc


class Reloj:
    def __init__(self) -> None:
        self.ahora = 100.0

    def __call__(self) -> float:
        return self.ahora


class Escenario:
    def __init__(self) -> None:
        self.falso = BackendFalso()
        self.reloj = Reloj()
        self.vinculadas: list[TokensPc] = []
        self.v = Vinculador(
            ClienteOAuth(URL_API, self.falso.transporte()),
            "Sala-Rosa",
            "Windows 11 Home",
            "0.5.0",
            self.vinculadas.append,
            self.reloj,
        )

    def avanzar(self, segundos: float) -> None:
        self.reloj.ahora += segundos
        self.v.paso()

    def sondeos(self) -> int:
        return sum(1 for s in self.falso.solicitudes if s.url.path == "/api/agente/token")


@pytest.fixture
def e() -> Escenario:
    return Escenario()


def test_muestra_el_codigo_y_lo_aprueba_el_celular(e: Escenario) -> None:
    assert e.v.estado().fase is Fase.PIDIENDO
    e.v.paso()
    estado = e.v.estado()
    assert estado.fase is Fase.CODIGO
    assert estado.codigo == e.falso.codigo_pendiente()
    assert estado.url == "app.tetengo.reqsai.tech/vincular"
    assert estado.url_completa == f"https://app.tetengo.reqsai.tech/vincular?codigo={estado.codigo}"
    assert estado.segundos == 600
    assert not estado.renovado
    e.avanzar(4)  # polls every ``interval`` (5 s), not sooner
    assert e.sondeos() == 0
    e.avanzar(1)
    assert e.sondeos() == 1  # authorization_pending
    assert e.v.estado().segundos == 595
    e.falso.aprobar()
    e.avanzar(5)
    assert e.v.fase is Fase.VINCULADA
    assert [t.pc_id for t in e.vinculadas] == ["pc-1"]


def test_slow_down_suma_cinco_segundos_para_siempre(
    e: Escenario, monkeypatch: pytest.MonkeyPatch
) -> None:
    e.v.paso()
    e.falso.intervalo = 5
    real = e.falso._oauth

    def lento(ruta: str, formulario: dict[str, str]):  # type: ignore[no-untyped-def]
        if formulario.get("grant_type", "").endswith("device_code") and e.sondeos() == 1:
            import httpx

            return httpx.Response(400, json={"error": "slow_down"})
        return real(ruta, formulario)

    monkeypatch.setattr(e.falso, "_oauth", lento)
    e.avanzar(5)  # slow_down → the interval becomes 10 s
    e.avanzar(5)
    assert e.sondeos() == 1
    e.avanzar(5)
    assert e.sondeos() == 2
    e.avanzar(5)
    assert e.sondeos() == 2  # still 10 s: for good
    e.avanzar(5)
    assert e.sondeos() == 3


def test_al_vencer_pide_un_codigo_nuevo_sin_que_nadie_lo_pida(e: Escenario) -> None:
    e.v.paso()
    primero = e.v.estado().codigo
    e.avanzar(600)
    estado = e.v.estado()
    assert estado.fase is Fase.CODIGO
    assert estado.codigo != primero
    assert estado.renovado  # «Código nuevo · el anterior venció» (CA-28.3)
    assert estado.segundos == 600


@pytest.mark.parametrize("motivo", ["expired_token", "invalid_grant"])
def test_codigo_vencido_o_usado_en_el_servidor(e: Escenario, motivo: str) -> None:
    e.v.paso()
    primero = e.v.estado().codigo
    if motivo == "expired_token":
        e.falso.vencer_codigos()
    else:
        e.falso._codigos.clear()
    e.avanzar(5)
    estado = e.v.estado()
    assert estado.codigo != primero
    assert estado.renovado


def test_no_reconozco_esta_pc(e: Escenario) -> None:
    e.v.paso()
    e.falso.rechazar()
    e.avanzar(5)
    assert e.v.fase is Fase.RECHAZADA
    assert e.v.estado().codigo is None
    pedidos = len(e.falso.vinculaciones)
    e.avanzar(60)
    assert len(e.falso.vinculaciones) == pedidos  # nothing until «Mostrar otro código»
    e.v.otro_codigo()
    e.v.paso()
    assert e.v.estado().fase is Fase.CODIGO
    assert not e.v.estado().renovado
    assert e.vinculadas == []


def test_sin_internet_reintenta_y_vuelve_al_mismo_codigo(e: Escenario) -> None:
    e.v.paso()
    codigo = e.v.estado().codigo
    e.falso.sin_conexion = True
    e.avanzar(5)
    estado = e.v.estado()
    assert estado.fase is Fase.SIN_INTERNET
    assert estado.codigo is None  # no QR while offline (D-28.1)
    assert estado.reintento == REINTENTO_S
    e.avanzar(10)
    assert e.v.estado().reintento == REINTENTO_S - 10
    e.falso.sin_conexion = False
    e.v.reintentar_ahora()  # «Reintentar ahora»
    e.v.paso()
    estado = e.v.estado()
    assert estado.fase is Fase.CODIGO
    assert estado.codigo == codigo  # still valid: a phone that scanned it can approve it


def test_sin_internet_al_empezar_y_servidor_caido(e: Escenario) -> None:
    e.falso.sin_conexion = True
    e.v.paso()
    assert e.v.fase is Fase.SIN_INTERNET
    e.falso.sin_conexion = False
    e.falso.fallos.append(503)
    e.avanzar(REINTENTO_S)
    assert e.v.estado().fase is Fase.SIN_SERVIDOR  # «Te Tengo no responde»
    e.avanzar(REINTENTO_S)
    assert e.v.estado().fase is Fase.CODIGO


def test_el_codigo_secreto_nunca_va_al_registro(
    e: Escenario, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    e.v.paso()
    e.falso.aprobar()
    e.avanzar(5)
    secretos = [k for k in e.falso._codigos]
    assert secretos
    for secreto in secretos:
        assert secreto not in caplog.text
    assert e.vinculadas[0].access_token not in caplog.text
    assert e.vinculadas[0].refresh_token not in caplog.text
    # The user code is shown on screen: logging it helps a headless install.
    assert "Código para vincular esta PC" in caplog.text
