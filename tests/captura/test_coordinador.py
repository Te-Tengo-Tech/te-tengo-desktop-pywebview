"""The PC's states and the moves between them (US-28, US-31), against the fake backend."""

import json
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from te_tengo_captura.agente import Agente
from te_tengo_captura.backend.cliente import ClienteBackend
from te_tengo_captura.backend.falso import URL_API, BackendFalso
from te_tengo_captura.captura.dispositivos import Dispositivo
from te_tengo_captura.captura.fuentes import FuenteFalsa
from te_tengo_captura.config import Configuracion
from te_tengo_captura.coordinador import Coordinador, Pantalla
from te_tengo_captura.vinculacion.credenciales import AlmacenCredenciales, LlaveroEnMemoria
from tests.captura.test_agente import SinPersonas

WEBCAMS = [
    Dispositivo("id-1", "Webcam USB HD", 0, 1200),
    Dispositivo("id-2", "Logitech C920", 1, 1200),
]


def esperar(prueba: Callable[[], object], limite_s: float = 15) -> None:
    fin = time.monotonic() + limite_s
    while not prueba():
        assert time.monotonic() < fin, "no ocurrió a tiempo"
        time.sleep(0.02)


class Escenario:
    def __init__(self, tmp_path: Path) -> None:
        self.falso = BackendFalso(credencial="credencial-1", intervalo=0)
        self.almacen = AlmacenCredenciales(LlaveroEnMemoria())
        self.datos = tmp_path / "datos"
        self.olvidadas = 0
        self.coordinador: Coordinador | None = None

    def crear(
        self, instalacion: Callable[[Callable[[str], None]], Agente] | None = None
    ) -> Coordinador:
        def olvidar() -> None:
            self.olvidadas += 1

        self.coordinador = Coordinador(
            "0.5.0",
            URL_API,
            self.datos,
            self.almacen,
            instalacion=instalacion,
            olvidar_instalacion=olvidar,
            transporte=self.falso.transporte(),
            canal_pc=False,
            listar=lambda: list(WEBCAMS),
        )
        return self.coordinador

    def vincular(self) -> Coordinador:
        c = self.crear()
        c.iniciar()
        esperar(lambda: self.falso.codigo_pendiente())
        self.falso.aprobar()
        esperar(lambda: c.estado().pantalla is Pantalla.VINCULADA)
        return c


@pytest.fixture
def e(tmp_path: Path) -> Iterator[Escenario]:
    escenario = Escenario(tmp_path)
    yield escenario
    if escenario.coordinador is not None:
        escenario.coordinador.detener()


def test_recien_instalada_muestra_el_codigo(e: Escenario) -> None:
    c = e.crear()
    c.iniciar()
    esperar(lambda: c.estado().a_json()["pair"]["code"])
    estado = c.estado()
    assert estado.pantalla is Pantalla.VINCULAR
    assert (estado.bandeja.k, estado.bandeja.etiqueta) == ("off", "sin vincular")
    datos = estado.a_json()
    assert datos["screen"] == "vincular"
    assert datos["pair"]["code"] == e.falso.codigo_pendiente()
    assert datos["pair"]["url"] == "app.tetengo.reqsai.tech/vincular"
    assert datos["pair"]["qr"]["n"] >= 21
    assert datos["pair"]["left"] == 600
    assert e.falso.vinculaciones[0]["nombre_pc"] == datos["pcname"]
    assert "device_code" not in json.dumps(datos)
    assert "dispositivo-secreto" not in json.dumps(datos)


def test_aprobada_en_el_celular_queda_vinculada(e: Escenario) -> None:
    c = e.vincular()
    assert e.almacen.leer() is not None  # tokens in the OS credential store
    esperar(lambda: c.estado().a_json().get("linkedBy"))
    datos = c.estado().a_json()
    assert datos["screen"] == "vinculada"
    assert datos["home"]["who"] == "Rosa Huamán"
    assert datos["linkedBy"] == "Carmen"
    assert sorted(d["name"] for d in datos["devices"]) == ["Logitech C920", "Webcam USB HD"]
    assert c.estado().bandeja.etiqueta == "falta elegir las cámaras en la app"
    c.ir_a_estado()
    estado = c.estado()
    assert estado.pantalla is Pantalla.PRINCIPAL
    assert estado.a_json()["unlink"] is True
    assert estado.a_json()["dataBytes"] >= 0  # «Borrar también los datos… (3,2 GB)»
    assert estado.agente is not None
    assert estado.agente.aviso.titulo_html == "Falta elegir las cámaras en la app"
    esperar(lambda: e.falso.senales_pc)  # «En línea» in the app with no camera (CA-30.2)
    assert e.falso.senales_pc[0]["versionAgente"] == "0.5.0"


def test_al_reiniciar_sigue_vinculada_sin_pedir_el_codigo(e: Escenario) -> None:
    c = e.vincular()
    c.detener()
    otro = e.crear()
    otro.iniciar()
    assert otro.estado().pantalla is Pantalla.PRINCIPAL  # CA-28.7
    assert len(e.falso.vinculaciones) == 1


def test_quitada_desde_la_app(e: Escenario) -> None:
    c = e.vincular()
    c.ir_a_estado()
    esperar(lambda: c.pc is not None and c.pc.latido.pc is not None)  # the household is known
    e.falso.quitar_pc()
    c.reintentar_ahora()  # the next request answers 401 PC_DESVINCULADA
    esperar(lambda: c.estado().pantalla is Pantalla.QUITADA)
    estado = c.estado()
    assert estado.quitada
    assert estado.a_json()["who"] == "Rosa Huamán"
    assert (estado.bandeja.k, estado.bandeja.etiqueta) == ("off", "se quitó de la vivienda")
    assert e.almacen.leer() is None  # credentials deleted (CA-31.1)
    assert not (e.datos / "pc.json").exists()
    # A restart still says it was removed until «Vincular de nuevo».
    c.detener()
    otro = e.crear()
    otro.iniciar()
    assert otro.estado().pantalla is Pantalla.QUITADA
    otro.vincular_de_nuevo()
    esperar(lambda: otro.estado().a_json().get("pair", {}).get("code"))
    assert otro.estado().pantalla is Pantalla.VINCULAR


def test_mensaje_desvincular_del_canal(e: Escenario) -> None:
    c = e.vincular()
    assert c.pc is not None
    c.pc.sesion.desvincular("desvincular")  # what the PC channel does on the message
    esperar(lambda: c.estado().pantalla is Pantalla.QUITADA)


@pytest.mark.parametrize("borrar", [False, True])
def test_desvincular_desde_esta_pc(e: Escenario, borrar: bool) -> None:
    c = e.vincular()
    c.ir_a_estado()
    (e.datos / "clips").mkdir(parents=True, exist_ok=True)
    resultado = c.desvincular(borrar)
    assert resultado == {"ok": True, "avisada": True}
    assert e.falso.desvinculaciones == [{"via": "delete", "datos": "true" if borrar else None}]
    assert e.almacen.leer() is None
    assert c.estado().pantalla is Pantalla.VINCULAR  # the code again (CA-31.3)
    assert not (e.datos / "clips").exists()


def test_desvincular_sin_internet_queda_pendiente_y_se_envia_despues(e: Escenario) -> None:
    c = e.vincular()
    c.ir_a_estado()
    e.falso.sin_conexion = True
    assert c.desvincular(True) == {"ok": True, "avisada": False}
    pendiente = e.almacen.leer_revocacion()
    assert pendiente is not None
    assert pendiente.datos_locales_borrados
    assert e.almacen.leer() is None
    e.falso.sin_conexion = False
    c.detener()
    otro = e.crear()
    otro.iniciar()
    esperar(lambda: e.almacen.leer_revocacion() is None)
    assert e.falso.desvinculaciones == [{"via": "revocacion", "datos": "true"}]


def test_noventa_dias_sin_conexion(e: Escenario) -> None:
    c = e.vincular()
    c.ir_a_estado()
    (e.datos / "ultimo_contacto.json").write_text(json.dumps({"en": time.time() - 91 * 86400}))
    e.falso.quitar_pc()  # the server unlinked it after 90 days: the refresh gives invalid_grant
    assert c.pc is not None
    c.pc.sesion.desvincular("invalid_grant")
    esperar(lambda: c.estado().a_json().get("pair", {}).get("re90"))
    assert c.estado().pantalla is Pantalla.VINCULAR


def test_rechazada_en_el_celular(e: Escenario) -> None:
    c = e.crear()
    c.iniciar()
    esperar(lambda: e.falso.codigo_pendiente())
    e.falso.rechazar()
    esperar(lambda: c.estado().pantalla is Pantalla.RECHAZADA)
    c.otro_codigo()
    esperar(lambda: c.estado().a_json().get("pair", {}).get("code"))


def test_una_instalacion_quitada_deja_de_capturar_y_olvida_su_credencial(
    e: Escenario, configuracion: Configuracion
) -> None:
    agentes: list[Agente] = []

    def instalar(al_desvincular: Callable[[str], None]) -> Agente:
        cliente = ClienteBackend(URL_API, "credencial-1", "Sala", "0.5.0", e.falso.transporte())
        agente = Agente(
            configuracion,
            cliente,
            FuenteFalsa(paso=1 / 8),
            SinPersonas(),
            e.datos,
            "0.5.0",
            codificar=lambda f: b"mp4",
            al_desvincular=al_desvincular,
        )
        agentes.append(agente)
        return agente

    c = e.crear(instalacion=instalar)
    c.iniciar()
    assert c.reintentar_ahora()
    assert agentes[0]._permitida()
    e.falso.quitar_instalacion()  # «Quitar esta PC» on «PC de la casa» in the app
    c.reintentar_ahora()
    assert not agentes[0]._permitida()  # capture stops at once (CA-31.1)
    esperar(lambda: c.estado().pantalla is Pantalla.QUITADA)
    assert e.olvidadas == 1  # the installation credential is deleted from config.toml
    assert c.estado().a_json()["who"] == "Rosa Huamán"
    c.vincular_de_nuevo()
    esperar(lambda: c.estado().pantalla is Pantalla.VINCULAR)


def test_modo_avanzado_apagado_por_defecto_y_anotado(e: Escenario) -> None:
    c = e.vincular()
    c.ir_a_estado()
    assert c.modo_avanzado is False  # CA-32.1
    assert c.estado().a_json()["advanced"] is False
    assert c.registro("x", 0) == []
    assert c.cambiar_modo_avanzado(True)
    assert c.diario.activo
    assert c.estado().a_json()["advanced"] is True
    lista = c.lista_actividad()
    assert lista[0]["m"] == "Desde esta PC: se activó el modo avanzado"
    assert lista[0]["who"] == "pc"
    assert c.pc is not None
    c.pc.reintentar_ahora()  # the heartbeat sends what is pending
    esperar(lambda: any(a["tipo"] == "MODO_AVANZADO_ACTIVADO" for a in e.falso.actividad.values()))
    esperar(lambda: not c.lista_actividad()[0]["pend"])
    esperar(lambda: any("vinculó la PC" in a["m"] for a in c.lista_actividad()))
    c.cambiar_modo_avanzado(False)
    assert not c.diario.activo


def test_diagnostico_desde_el_coordinador(e: Escenario, tmp_path: Path) -> None:
    c = e.vincular()
    c.ir_a_estado()
    nombre = c.nombre_diagnostico()
    assert nombre.startswith("te-tengo-diagnostico-")
    assert nombre.endswith(".zip")
    r = c.exportar_diagnostico(tmp_path / nombre)
    assert r["ok"] is True
    assert r["tamano"] > 0
    import zipfile

    with zipfile.ZipFile(tmp_path / nombre) as archivo:
        datos = json.loads(archivo.read("diagnostico.json"))
        contenido = b"".join(archivo.read(n) for n in archivo.namelist())
    assert datos["modo"] == "pc"
    assert datos["programa"] == "Te Tengo Captura 0.5.0"
    assert c.pc is not None
    for secreto in c.pc.sesion.secretos():
        assert secreto.encode() not in contenido
