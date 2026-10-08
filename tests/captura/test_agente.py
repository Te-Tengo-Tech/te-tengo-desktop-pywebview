import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from te_tengo_captura.agente import Agente
from te_tengo_captura.backend.cliente import ClienteBackend
from te_tengo_captura.backend.falso import URL_API, BackendFalso
from te_tengo_captura.backend.modelos import ModoVista
from te_tengo_captura.backend.transmision import url_websocket
from te_tengo_captura.captura.fuentes import FuenteFalsa, Imagen
from te_tengo_captura.config import Configuracion
from te_tengo_captura.estado import EstadoAgente, Situacion
from te_tengo_deteccion.pose.schemas import Pose

AHORA = datetime(2026, 10, 7, 14, 0, tzinfo=UTC)


class SinPersonas:
    def estimar(self, imagen: Imagen, instante_ms: int) -> Pose | None:
        return None

    def reiniciar(self) -> None:
        pass

    def cerrar(self) -> None:
        pass


class Escenario:
    def __init__(self, tmp_path: Path, configuracion: Configuracion) -> None:
        self.backend = BackendFalso(credencial="cambia-esta-credencial")
        self.fuente = FuenteFalsa(paso=1 / 8)
        self.ahora = AHORA
        cliente = ClienteBackend(
            URL_API, self.backend.credencial, "Sala", "1.0.0", self.backend.transporte()
        )
        self.agente = Agente(
            configuracion,
            cliente,
            self.fuente,
            SinPersonas(),
            tmp_path,
            "1.0.0",
            reloj_utc=lambda: self.ahora,
            codificar=lambda f: b"mp4",
        )


@pytest.fixture
def e(tmp_path: Path, configuracion: Configuracion) -> Escenario:
    return Escenario(tmp_path, configuracion)


def test_estado_inicial_antes_del_primer_latido(e: Escenario) -> None:
    estado = e.agente.estado()
    assert estado.situacion is Situacion.SIN_CONSENTIMIENTO  # CA-05.2: nothing known yet
    assert estado.a_json()["listo"] is False
    assert estado.entradas.nombre_habitacion == "Sala"


def test_reintentar_ahora_conecta_y_permite_capturar(e: Escenario) -> None:
    assert e.agente.reintentar_ahora()
    assert e.agente.estado().situacion is Situacion.ENVIANDO
    e.ahora += timedelta(seconds=7)
    assert e.agente.estado().entradas.segundos_desde_envio == 7


def test_sin_internet(e: Escenario) -> None:
    e.backend.sin_conexion = True
    assert not e.agente.reintentar_ahora()
    estado = e.agente.estado()
    assert estado.situacion is Situacion.SIN_INTERNET
    assert estado.entradas.segundos_para_reintento == 2


def test_pausa_y_nombre_desde_el_backend(e: Escenario) -> None:
    e.backend.pausar(AHORA + timedelta(hours=1))
    e.backend.nombre_habitacion = "Dormitorio"
    e.agente.reintentar_ahora()
    estado = e.agente.estado()
    assert estado.situacion is Situacion.EN_PAUSA
    assert estado.entradas.nombre_habitacion == "Dormitorio"


def test_webcam_desconectada(e: Escenario) -> None:
    e.agente.reintentar_ahora()
    e.fuente.conectada = False
    e.agente.bucle.paso()
    assert e.agente.estado().situacion is Situacion.WEBCAM_DESCONECTADA
    assert not e.agente.buscar_webcam(espera_s=0)
    e.fuente.conectada = True
    e.agente.bucle.paso()
    assert e.agente.estado().situacion is Situacion.ENVIANDO


def test_hilos_publican_el_estado_y_se_detienen(e: Escenario) -> None:
    recibidos: list[EstadoAgente] = []
    listo = threading.Event()

    def oyente(estado: EstadoAgente) -> None:
        recibidos.append(estado)
        if estado.situacion is Situacion.ENVIANDO:
            listo.set()

    def roto(estado: EstadoAgente) -> None:
        raise RuntimeError("la ventana falló")

    e.agente.suscribir(roto)
    e.agente.suscribir(oyente)
    e.agente.iniciar()
    assert listo.wait(5)
    assert e.agente.buscar_webcam(espera_s=5)
    e.agente.detener()
    assert e.backend.senales


class PublicadorGrabado:
    def __init__(self, url: str) -> None:
        self.url = url
        self.instantes: list[float] = []
        self.cerrado = False

    def publicar(self, imagen: Imagen, instante: float) -> None:
        self.instantes.append(instante)

    def cerrar(self) -> None:
        self.cerrado = True


def test_vista_en_vivo_con_la_captura_y_su_pausa(e: Escenario) -> None:
    publicadores: list[PublicadorGrabado] = []

    def abrir(url: str) -> PublicadorGrabado:
        publicadores.append(PublicadorGrabado(url))
        return publicadores[-1]

    e.agente.en_vivo._abrir_publicador = abrir
    e.agente.reintentar_ahora()  # capture allowed
    e.agente.en_vivo.transmitir(
        "rtsp://m:8554/camaras/camara-1", "agente", "clave-pub", ModoVista.VIDEO
    )
    assert "clave-pub" in e.agente.secretos()
    e.agente.bucle.paso()
    e.agente.en_vivo.procesar_siguiente(0)
    assert len(publicadores[0].instantes) == 1

    e.backend.pausar(AHORA + timedelta(hours=1))
    e.agente.reintentar_ahora()
    e.agente.bucle.paso()  # the gate closes the webcam and suspends the live view
    e.agente.en_vivo.procesar_siguiente(0)
    assert publicadores[0].cerrado
    e.agente.bucle.paso()
    e.agente.en_vivo.procesar_siguiente(0)
    assert len(publicadores) == 1


def test_el_canal_de_vista_en_vivo_solo_con_el_backend_real(
    tmp_path: Path, configuracion: Configuracion
) -> None:
    backend = BackendFalso(credencial="c")
    cliente = ClienteBackend(URL_API, "c", "Sala", "1.0.0", backend.transporte())
    sin_canal = Agente(configuracion, cliente, FuenteFalsa(), SinPersonas(), tmp_path, "1.0.0")
    assert sin_canal._canal is None
    con_canal = Agente(
        configuracion, cliente, FuenteFalsa(), SinPersonas(), tmp_path, "1.0.0", vista_en_vivo=True
    )
    assert con_canal._canal is not None
    assert con_canal._canal._url == url_websocket(configuracion.api_url)
