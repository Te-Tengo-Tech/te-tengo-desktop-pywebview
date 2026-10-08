import logging
import threading
import time

import numpy as np
import pytest

from te_tengo_captura.backend.modelos import ModoVista
from te_tengo_captura.captura.en_vivo import TransmisionEnVivo
from te_tengo_captura.captura.fuentes import Fotograma, Imagen
from te_tengo_captura.captura.postura import BLANCO, DURAZNO, MORADO
from te_tengo_captura.captura.publicador import url_con_credenciales
from tests import fabricas

URL = "rtsp://mediamtx:8554/camaras/camara-1"
CLAVE = "clave-de-publicacion"


class PublicadorFalso:
    def __init__(self, url: str, fallar: bool = False) -> None:
        self.url = url
        self.fallar = fallar
        self.imagenes: list[Imagen] = []
        self.instantes: list[float] = []
        self.cerrado = False

    def publicar(self, imagen: Imagen, instante: float) -> None:
        if self.fallar:
            raise ConnectionRefusedError(61, "Connection refused")
        self.imagenes.append(imagen)
        self.instantes.append(instante)

    def cerrar(self) -> None:
        self.cerrado = True


class Escenario:
    def __init__(self) -> None:
        self.permitida = True
        self.ahora = 0.0
        self.fallar = False
        self.publicadores: list[PublicadorFalso] = []
        self.vivo = TransmisionEnVivo(
            permitida=lambda: self.permitida,
            abrir_publicador=self._abrir,
            reloj=lambda: self.ahora,
        )
        self.instante = 0.0

    def _abrir(self, url: str) -> PublicadorFalso:
        publicador = PublicadorFalso(url, self.fallar)
        self.publicadores.append(publicador)
        return publicador

    @property
    def ultimo(self) -> PublicadorFalso:
        return self.publicadores[-1]

    def fotograma(self, semilla: int = 0) -> Fotograma:
        self.instante += 1 / 8
        generador = np.random.default_rng(semilla)
        imagen = generador.integers(0, 256, (480, 640, 3), dtype=np.uint8)
        return Fotograma(self.instante, b"", imagen)

    def cuadro(self, semilla: int = 0) -> None:
        """The capture loop hands one frame and the worker processes it."""
        if self.vivo.activo:
            self.vivo.enviar(self.fotograma(semilla), fabricas.DE_PIE)
        self.vivo.procesar_siguiente(0)


@pytest.fixture
def e() -> Escenario:
    return Escenario()


def test_sin_solicitud_no_esta_activo_ni_publica(e: Escenario) -> None:
    assert not e.vivo.activo
    e.vivo.enviar(e.fotograma(), None)  # even if a frame arrives
    e.vivo.procesar_siguiente(0)
    assert e.publicadores == []


def test_publica_en_la_url_con_las_credenciales(e: Escenario) -> None:
    e.vivo.transmitir(URL, "agente", CLAVE, ModoVista.VIDEO)
    assert e.vivo.activo
    for _ in range(3):
        e.cuadro()
    assert len(e.publicadores) == 1
    assert e.ultimo.url == f"rtsp://agente:{CLAVE}@mediamtx:8554/camaras/camara-1"
    assert e.ultimo.instantes == [0.125, 0.25, 0.375]
    assert e.vivo.publicando
    assert e.vivo.publicados == 3


def test_modo_video_publica_el_fotograma(e: Escenario) -> None:
    e.vivo.transmitir(URL, "agente", CLAVE, ModoVista.VIDEO)
    fotograma = e.fotograma(semilla=9)
    e.vivo.enviar(fotograma, fabricas.DE_PIE)
    e.vivo.procesar_siguiente(0)
    assert np.array_equal(e.ultimo.imagenes[0], fotograma.imagen)


def test_solo_postura_no_publica_pixeles_de_la_camara(e: Escenario) -> None:
    e.vivo.transmitir(URL, "agente", CLAVE, ModoVista.SOLO_POSTURA)
    for semilla in range(4):
        e.cuadro(semilla)
    marca = {MORADO, BLANCO, DURAZNO}
    for imagen in e.ultimo.imagenes:
        colores = {tuple(int(c) for c in p) for p in np.unique(imagen.reshape(-1, 3), axis=0)}
        assert colores <= marca
    assert all(np.array_equal(i, e.ultimo.imagenes[0]) for i in e.ultimo.imagenes)


def test_cambiar_de_modo_no_reconecta(e: Escenario) -> None:
    e.vivo.transmitir(URL, "agente", CLAVE, ModoVista.VIDEO)
    e.cuadro(1)
    e.vivo.cambiar_modo(ModoVista.SOLO_POSTURA)
    e.cuadro(2)
    assert len(e.publicadores) == 1
    assert e.vivo.modo is ModoVista.SOLO_POSTURA
    colores = np.unique(e.ultimo.imagenes[1].reshape(-1, 3), axis=0)
    assert len(colores) <= 3


def test_transmitir_false_cierra_la_publicacion(e: Escenario) -> None:
    e.vivo.transmitir(URL, "agente", CLAVE, ModoVista.VIDEO_CON_POSTURA)
    e.cuadro()
    e.vivo.enviar(e.fotograma(), None)  # queued just before the stop
    e.vivo.detener()
    assert not e.vivo.activo
    e.vivo.procesar_siguiente(0)
    assert e.ultimo.cerrado
    assert len(e.ultimo.imagenes) == 1
    assert not e.vivo.publicando
    assert e.vivo.modo is ModoVista.VIDEO


def test_al_suspender_la_captura_se_cierra_y_luego_se_reanuda(e: Escenario) -> None:
    e.vivo.transmitir(URL, "agente", CLAVE, ModoVista.VIDEO)
    e.cuadro()
    e.vivo.enviar(e.fotograma(), None)
    e.permitida = False  # paused or consent revoked (CA-23.4)
    e.vivo.suspender()
    e.vivo.procesar_siguiente(0)
    assert e.ultimo.cerrado
    assert len(e.ultimo.imagenes) == 1  # the queued frame was dropped
    e.permitida = True
    e.cuadro()
    assert len(e.publicadores) == 2  # still requested: a new connection
    assert len(e.ultimo.imagenes) == 1


def test_sin_permiso_cierra_aunque_no_lleguen_fotogramas(e: Escenario) -> None:
    e.vivo.transmitir(URL, "agente", CLAVE, ModoVista.VIDEO)
    e.cuadro()
    e.permitida = False
    e.vivo.procesar_siguiente(0)  # nothing queued: the worker checks the gate itself
    assert e.ultimo.cerrado


def test_sin_permiso_no_publica_lo_que_llegue(e: Escenario) -> None:
    e.vivo.transmitir(URL, "agente", CLAVE, ModoVista.VIDEO)
    e.permitida = False
    e.cuadro()
    assert e.publicadores == []


def test_una_nueva_solicitud_reconecta(e: Escenario) -> None:
    e.vivo.transmitir(URL, "agente", CLAVE, ModoVista.VIDEO)
    e.cuadro()
    e.vivo.transmitir(URL, "agente", "otra-clave", ModoVista.VIDEO)
    e.cuadro()
    assert e.publicadores[0].cerrado
    assert e.ultimo.url.endswith("agente:otra-clave@mediamtx:8554/camaras/camara-1")


def test_si_falla_reintenta_con_espera_creciente(
    e: Escenario, caplog: pytest.LogCaptureFixture
) -> None:
    e.fallar = True
    e.vivo.transmitir(URL, "agente", CLAVE, ModoVista.VIDEO)
    with caplog.at_level(logging.INFO):
        e.cuadro()
    assert len(e.publicadores) == 1
    assert e.ultimo.cerrado
    assert CLAVE not in caplog.text
    assert "reintento en 1 s" in caplog.text
    e.ahora = 0.5
    e.cuadro()  # still waiting: dropped
    assert len(e.publicadores) == 1
    e.ahora = 1.0
    e.cuadro()
    assert len(e.publicadores) == 2
    e.ahora = 2.5  # the second wait is 2 s
    e.cuadro()
    assert len(e.publicadores) == 2
    e.fallar = False
    e.ahora = 3.0
    e.cuadro()
    assert len(e.publicadores) == 3
    assert e.vivo.publicando


def test_enviar_nunca_bloquea_y_descarta_lo_mas_viejo(e: Escenario) -> None:
    e.vivo.transmitir(URL, "agente", CLAVE, ModoVista.VIDEO)
    fotogramas = [e.fotograma() for _ in range(50)]
    inicio = time.perf_counter()
    for fotograma in fotogramas:
        e.vivo.enviar(fotograma, None)  # nobody consumes: the publisher is far behind
    assert time.perf_counter() - inicio < 0.5
    assert e.vivo.descartados == 48
    e.vivo.procesar_siguiente(0)
    e.vivo.procesar_siguiente(0)
    assert e.ultimo.instantes == [fotogramas[-2].instante, fotogramas[-1].instante]


def test_la_clave_es_un_secreto_mientras_dura_la_solicitud(e: Escenario) -> None:
    assert e.vivo.secretos() == []
    e.vivo.transmitir(URL, "agente", CLAVE, ModoVista.VIDEO)
    assert e.vivo.secretos() == [CLAVE]
    e.vivo.detener()
    assert e.vivo.secretos() == []


def test_el_hilo_publica_y_se_cierra() -> None:
    publicados = threading.Event()
    publicadores: list[PublicadorFalso] = []

    def abrir(url: str) -> PublicadorFalso:
        publicador = PublicadorFalso(url)
        publicador.publicar = lambda imagen, instante: publicados.set()  # type: ignore[method-assign]
        publicadores.append(publicador)
        return publicador

    vivo = TransmisionEnVivo(permitida=lambda: True, abrir_publicador=abrir)
    vivo.iniciar()
    vivo.transmitir(URL, None, None, ModoVista.VIDEO)
    vivo.enviar(Fotograma(0.0, b"", np.zeros((480, 640, 3), dtype=np.uint8)), None)
    assert publicados.wait(2)
    vivo.cerrar()
    assert publicadores[0].cerrado
    assert publicadores[0].url == URL  # no credentials, no userinfo


def test_cerrar_sin_iniciar() -> None:
    TransmisionEnVivo(permitida=lambda: True).cerrar()


@pytest.mark.parametrize(
    ("url", "usuario", "clave", "esperada"),
    [
        (URL, "agente", "abc", "rtsp://agente:abc@mediamtx:8554/camaras/camara-1"),
        (URL, "agente", "a/b:c@d", "rtsp://agente:a%2Fb%3Ac%40d@mediamtx:8554/camaras/camara-1"),
        (
            "rtsps://vivo.example:8322/camaras/x",
            "agente",
            None,
            "rtsps://agente@vivo.example:8322/camaras/x",
        ),
        ("rtsp://[::1]:8554/camaras/x", "agente", "k", "rtsp://agente:k@[::1]:8554/camaras/x"),
        ("rtsp://old:pw@host/camaras/x", "agente", "k", "rtsp://agente:k@host/camaras/x"),
        (URL, None, "k", URL),
    ],
)
def test_url_con_credenciales(
    url: str, usuario: str | None, clave: str | None, esperada: str
) -> None:
    assert url_con_credenciales(url, usuario, clave) == esperada
