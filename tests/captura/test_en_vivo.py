import logging
import threading
import time
from itertools import pairwise

import numpy as np
import pytest

from te_tengo_captura.backend.modelos import ModoVista
from te_tengo_captura.captura.en_vivo import (
    FRESCURA_S,
    PREPARACION_S,
    Ritmo,
    TransmisionEnVivo,
    marcar_tiempo,
)
from te_tengo_captura.captura.fuentes import Imagen
from te_tengo_captura.captura.postura import BLANCO, DURAZNO, MORADO
from te_tengo_captura.captura.publicador import url_con_credenciales
from tests import fabricas

URL = "rtsp://mediamtx:8554/camaras/camara-1"
CLAVE = "clave-de-publicacion"
WEBCAM = 1 / 30  # the fake webcam delivers 30 fps


class PublicadorFalso:
    def __init__(self, url: str, fps: float, fallar: bool = False) -> None:
        self.url = url
        self.fps = fps
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
    def __init__(self, marca_tiempo: bool = False) -> None:
        self.permitida = True
        self.ahora = 0.0
        self.fallar = False
        self.publicadores: list[PublicadorFalso] = []
        self.calentados: list[tuple[int, int, float]] = []
        self.resueltos: list[tuple[str, int]] = []
        self.vivo = TransmisionEnVivo(
            permitida=lambda: self.permitida,
            abrir_publicador=self._abrir,
            marca_tiempo=marca_tiempo,
            calentar=lambda ancho, alto, fps: self.calentados.append((ancho, alto, fps)),
            resolver=lambda host, puerto: self.resueltos.append((host, puerto)),
            reloj=lambda: self.ahora,
            reloj_pared=lambda: 1_760_000_000.123,
        )
        self.instante = 100.0  # a webcam's monotonic clock

    def _abrir(self, url: str, fps: float) -> PublicadorFalso:
        publicador = PublicadorFalso(url, fps, self.fallar)
        self.publicadores.append(publicador)
        return publicador

    @property
    def ultimo(self) -> PublicadorFalso:
        return self.publicadores[-1]

    def imagen(self, semilla: int = 0, forma: tuple[int, int] = (480, 640)) -> Imagen:
        generador = np.random.default_rng(semilla)
        return generador.integers(0, 256, (*forma, 3), dtype=np.uint8)

    def webcam(self, cuadros: int = 1, semilla: int = 0) -> None:
        """``cuadros`` webcam frames at 30 fps, each followed by one step of the worker."""
        for _ in range(cuadros):
            self.instante += WEBCAM
            self.ahora += WEBCAM
            self.vivo.ofrecer(self.instante, self.imagen(semilla))
            self.vivo.procesar_siguiente(0)


@pytest.fixture
def e() -> Escenario:
    return Escenario()


def test_sin_solicitud_no_esta_activo_ni_publica(e: Escenario) -> None:
    assert not e.vivo.activo
    e.webcam(6)  # even if frames arrive
    assert e.publicadores == []
    assert e.calentados == []


def test_publica_a_15_fps_desde_una_webcam_de_30(e: Escenario) -> None:
    e.vivo.transmitir(URL, "agente", CLAVE, ModoVista.VIDEO)
    assert e.vivo.activo
    e.webcam(30)
    assert len(e.publicadores) == 1
    assert e.ultimo.url == f"rtsp://agente:{CLAVE}@mediamtx:8554/camaras/camara-1"
    assert e.ultimo.fps == 15
    assert len(e.ultimo.instantes) == 15
    intervalos = {round(b - a, 6) for a, b in pairwise(e.ultimo.instantes)}
    assert intervalos == {round(1 / 15, 6)}  # constant rate, on the grid
    assert e.vivo.publicando
    assert e.vivo.publicados == 15


def test_publica_la_imagen_de_la_webcam_a_480p(e: Escenario) -> None:
    e.vivo.transmitir(URL, "agente", CLAVE, ModoVista.VIDEO)
    imagen = e.imagen(9, (720, 1280))
    e.vivo.ofrecer(1.0, imagen)
    e.vivo.procesar_siguiente(0)
    assert e.ultimo.imagenes[0].shape == (480, 854, 3)
    e.vivo.ofrecer(2.0, pequena := e.imagen(3))
    e.vivo.procesar_siguiente(0)
    assert np.array_equal(e.ultimo.imagenes[1], pequena)
    assert np.array_equal(imagen, e.imagen(9, (720, 1280)))  # the webcam's frame is untouched


def test_el_esqueleto_usa_la_ultima_pose(e: Escenario) -> None:
    e.vivo.transmitir(URL, "agente", CLAVE, ModoVista.VIDEO_CON_POSTURA)
    e.webcam(1)
    e.vivo.anotar_pose(fabricas.DE_PIE)
    e.webcam(2)
    e.vivo.anotar_pose(None)  # nobody seen
    e.webcam(2)
    original = e.imagen()
    sin_esqueleto, con_esqueleto, sin_persona = e.ultimo.imagenes
    assert np.array_equal(sin_esqueleto, original)
    assert not np.array_equal(con_esqueleto, original)
    assert np.array_equal(sin_persona, original)


def test_solo_postura_no_publica_pixeles_de_la_camara(e: Escenario) -> None:
    e.vivo.transmitir(URL, "agente", CLAVE, ModoVista.SOLO_POSTURA)
    e.vivo.anotar_pose(fabricas.DE_PIE)
    for semilla in range(8):
        e.webcam(1, semilla)
    marca = {MORADO, BLANCO, DURAZNO}
    assert e.ultimo.imagenes
    for imagen in e.ultimo.imagenes:
        colores = {tuple(int(c) for c in p) for p in np.unique(imagen.reshape(-1, 3), axis=0)}
        assert colores <= marca
    assert all(np.array_equal(i, e.ultimo.imagenes[0]) for i in e.ultimo.imagenes)


def test_cambiar_de_modo_no_reconecta(e: Escenario) -> None:
    e.vivo.transmitir(URL, "agente", CLAVE, ModoVista.VIDEO)
    e.webcam(2)
    e.vivo.cambiar_modo(ModoVista.SOLO_POSTURA)
    e.webcam(2)
    assert len(e.publicadores) == 1
    assert e.vivo.modo is ModoVista.SOLO_POSTURA
    colores = np.unique(e.ultimo.imagenes[1].reshape(-1, 3), axis=0)
    assert len(colores) <= 3


def test_transmitir_false_cierra_la_publicacion(e: Escenario) -> None:
    e.vivo.transmitir(URL, "agente", CLAVE, ModoVista.VIDEO_CON_POSTURA)
    e.webcam(2)
    e.instante += 1 / 15
    e.vivo.ofrecer(e.instante, e.imagen())  # queued just before the stop
    e.vivo.detener()
    assert not e.vivo.activo
    e.vivo.procesar_siguiente(0)
    assert e.ultimo.cerrado
    assert len(e.ultimo.imagenes) == 1
    assert not e.vivo.publicando
    assert e.vivo.modo is ModoVista.VIDEO


def test_al_suspender_la_captura_se_cierra_y_luego_se_reanuda(e: Escenario) -> None:
    e.vivo.transmitir(URL, "agente", CLAVE, ModoVista.VIDEO)
    e.webcam(2)
    e.instante += 1 / 15
    e.vivo.ofrecer(e.instante, e.imagen())
    e.permitida = False  # paused or consent revoked (CA-23.4)
    e.vivo.suspender()
    e.vivo.procesar_siguiente(0)
    assert e.ultimo.cerrado
    assert len(e.ultimo.imagenes) == 1  # the queued frame was dropped
    e.permitida = True
    e.webcam(2)
    assert len(e.publicadores) == 2  # still requested: a new connection
    assert len(e.ultimo.imagenes) == 1


def test_sin_permiso_cierra_aunque_no_lleguen_fotogramas(e: Escenario) -> None:
    e.vivo.transmitir(URL, "agente", CLAVE, ModoVista.VIDEO)
    e.webcam(1)
    e.permitida = False
    e.vivo.procesar_siguiente(0)  # nothing queued: the worker checks the gate itself
    assert e.ultimo.cerrado


def test_sin_permiso_no_publica_lo_que_llegue(e: Escenario) -> None:
    e.vivo.transmitir(URL, "agente", CLAVE, ModoVista.VIDEO)
    e.permitida = False
    e.webcam(4)
    assert e.publicadores == []


def test_una_nueva_solicitud_reconecta(e: Escenario) -> None:
    e.vivo.transmitir(URL, "agente", CLAVE, ModoVista.VIDEO)
    e.webcam(2)
    e.vivo.transmitir(URL, "agente", "otra-clave", ModoVista.VIDEO)
    e.webcam(2)
    assert e.publicadores[0].cerrado
    assert e.ultimo.url.endswith("agente:otra-clave@mediamtx:8554/camaras/camara-1")
    assert e.ultimo.instantes  # the new publication has its own start


def test_si_falla_reintenta_con_espera_creciente(
    e: Escenario, caplog: pytest.LogCaptureFixture
) -> None:
    e.fallar = True
    e.vivo.transmitir(URL, "agente", CLAVE, ModoVista.VIDEO)
    with caplog.at_level(logging.INFO):
        e.webcam(1)
    assert len(e.publicadores) == 1
    assert e.ultimo.cerrado
    assert CLAVE not in caplog.text
    assert "reintento en 1 s" in caplog.text
    e.webcam(12)  # 0.4 s: still waiting, frames dropped
    assert len(e.publicadores) == 1
    e.webcam(20)  # 1 s after the failure
    assert len(e.publicadores) == 2
    e.webcam(30)  # the second wait is 2 s
    assert len(e.publicadores) == 2
    e.fallar = False
    e.webcam(32)
    assert len(e.publicadores) == 3
    assert e.vivo.publicando


def test_ofrecer_nunca_bloquea_y_descarta_lo_mas_viejo(e: Escenario) -> None:
    e.vivo.transmitir(URL, "agente", CLAVE, ModoVista.VIDEO)
    imagen = e.imagen()
    inicio = time.perf_counter()
    for i in range(100):  # nobody consumes: the publisher is far behind
        e.vivo.ofrecer(100 + i * WEBCAM, imagen)
    assert time.perf_counter() - inicio < 0.5
    assert e.vivo.descartados == 48  # 50 frames taken at 15 fps, 2 queued
    e.vivo.procesar_siguiente(0)
    e.vivo.procesar_siguiente(0)
    e.vivo.procesar_siguiente(0)
    assert e.ultimo.instantes == pytest.approx([48 / 15, 49 / 15])  # the newest two slots


def test_la_clave_es_un_secreto_mientras_dura_la_solicitud(e: Escenario) -> None:
    assert e.vivo.secretos() == []
    e.vivo.transmitir(URL, "agente", CLAVE, ModoVista.VIDEO)
    assert e.vivo.secretos() == [CLAVE]
    e.vivo.detener()
    assert e.vivo.secretos() == []


def test_marca_de_tiempo_de_depuracion() -> None:
    e = Escenario(marca_tiempo=True)
    e.vivo.transmitir(URL, None, None, ModoVista.VIDEO)
    e.webcam(1)
    publicada = e.ultimo.imagenes[0]
    assert not np.array_equal(publicada, e.imagen())
    assert np.array_equal(publicada[240:], e.imagen()[240:])  # only the top-left corner
    assert np.array_equal(publicada, marcar_tiempo(e.imagen(), 1_760_000_000.123))


def test_sin_marca_de_tiempo_por_defecto(e: Escenario) -> None:
    e.vivo.transmitir(URL, None, None, ModoVista.VIDEO)
    e.webcam(1)
    assert np.array_equal(e.ultimo.imagenes[0], e.imagen())


# ---------------------------------------------------------------- pre-warm («preparar»)


def test_preparar_calienta_sin_publicar_ni_conectar(e: Escenario) -> None:
    e.vivo.preparar()
    assert e.vivo.activo
    assert e.vivo.preparada
    e.webcam(60)  # 2 s of webcam
    assert e.publicadores == []  # no frame leaves the PC before «transmitir»
    assert e.calentados == [(640, 480, 15)]  # once: what it loads stays loaded
    assert e.resueltos == []  # no publish host known yet
    assert e.vivo.secretos() == []


def test_transmitir_tras_preparar_publica_el_ultimo_cuadro_sin_esperar(e: Escenario) -> None:
    e.vivo.preparar()
    e.webcam(10)
    e.vivo.transmitir(URL, "agente", CLAVE, ModoVista.VIDEO)
    assert not e.vivo.preparada
    e.vivo.procesar_siguiente(0)  # woken by «transmitir»: no new webcam frame needed
    assert len(e.ultimo.instantes) == 1
    assert np.array_equal(e.ultimo.imagenes[0], e.imagen())
    e.webcam(4)
    assert len(e.ultimo.instantes) == 3
    assert len(e.publicadores) == 1


def test_un_cuadro_preparado_viejo_no_se_publica(e: Escenario) -> None:
    e.vivo.preparar()
    e.webcam(1)
    e.ahora += FRESCURA_S + 0.1  # the webcam stalled
    e.vivo.transmitir(URL, "agente", CLAVE, ModoVista.VIDEO)
    e.vivo.procesar_siguiente(0)
    assert e.publicadores == []
    e.webcam(2)  # the next live frame
    assert len(e.ultimo.instantes) == 1


def test_la_preparacion_vence_a_los_60_s(e: Escenario, caplog: pytest.LogCaptureFixture) -> None:
    e.vivo.preparar()
    e.webcam(1)
    e.ahora += PREPARACION_S
    with caplog.at_level(logging.INFO):
        e.vivo.procesar_siguiente(0)
    assert not e.vivo.activo
    assert "preparación vencida" in caplog.text
    e.vivo.transmitir(URL, "agente", CLAVE, ModoVista.VIDEO)
    e.vivo.procesar_siguiente(0)
    assert e.publicadores == []  # the warm frame went away with the warm state


def test_preparar_de_nuevo_extiende_el_plazo(e: Escenario) -> None:
    e.vivo.preparar()
    e.ahora += PREPARACION_S - 1
    e.vivo.preparar()
    e.ahora += 2
    e.vivo.procesar_siguiente(0)
    assert e.vivo.preparada


@pytest.mark.parametrize("motivo", ["detener", "suspender", "sin_permiso"])
def test_la_preparacion_se_descarta(e: Escenario, motivo: str) -> None:
    e.vivo.preparar()
    e.vivo.anotar_pose(fabricas.DE_PIE)
    e.webcam(3)
    if motivo == "detener":  # {"transmitir": false} or a closed channel
        e.vivo.detener()
    elif motivo == "suspender":  # the capture loop: pause or consent revoked
        e.vivo.suspender()
    else:  # the worker sees the gate closed before the loop does
        e.permitida = False
        e.vivo.procesar_siguiente(0)
        e.permitida = True
    assert not e.vivo.activo
    e.vivo.procesar_siguiente(0)  # the worker lets the warm frame go on its next step
    assert e.vivo._ultimo is None
    assert e.vivo._pose is None
    e.vivo.transmitir(URL, "agente", CLAVE, ModoVista.VIDEO)
    e.vivo.procesar_siguiente(0)
    assert e.publicadores == []


def test_preparar_durante_una_transmision_no_cambia_nada(e: Escenario) -> None:
    e.vivo.transmitir(URL, "agente", CLAVE, ModoVista.VIDEO)
    e.webcam(2)
    e.vivo.preparar()
    assert not e.vivo.preparada
    e.webcam(2)
    assert len(e.publicadores) == 1
    assert len(e.ultimo.instantes) == 2


def test_preparar_resuelve_el_servidor_de_la_ultima_transmision(e: Escenario) -> None:
    e.vivo.transmitir("rtsps://vivo.example:8322/camaras/x", "agente", CLAVE, ModoVista.VIDEO)
    e.vivo.detener()
    e.vivo.preparar()
    e.vivo.transmitir("rtsp://otro.example/camaras/x", "agente", CLAVE, ModoVista.VIDEO)
    e.vivo.detener()
    e.vivo.preparar()
    assert e.resueltos == [("vivo.example", 8322), ("otro.example", 554)]


def test_si_calentar_falla_igual_transmite(e: Escenario, caplog: pytest.LogCaptureFixture) -> None:
    def fallar(ancho: int, alto: int, fps: float) -> None:
        raise RuntimeError("sin libx264")

    e.vivo._calentar = fallar
    e.vivo.preparar()
    with caplog.at_level(logging.WARNING):
        e.webcam(2)
    assert "no se pudo preparar el codificador" in caplog.text
    e.vivo.transmitir(URL, "agente", CLAVE, ModoVista.VIDEO)
    e.vivo.procesar_siguiente(0)
    assert len(e.ultimo.instantes) == 1


def test_calienta_con_el_tamano_publicado() -> None:
    e = Escenario()
    e.vivo.preparar()
    e.vivo.ofrecer(1.0, e.imagen(0, (1080, 1920)))
    e.vivo.procesar_siguiente(0)
    assert e.calentados == [(854, 480, 15)]


# ---------------------------------------------------------------- constant rate


@pytest.mark.parametrize(
    ("fuente_fps", "esperados"),
    [(30, 15), (60, 15), (25, 15), (15, 15), (10, 10)],
)
def test_ritmo_toma_15_fps_de_cualquier_webcam(fuente_fps: float, esperados: int) -> None:
    ritmo = Ritmo(15)
    generador = np.random.default_rng(1)
    numeros = []
    for i in range(round(fuente_fps * 10)):  # 10 s
        jitter = generador.uniform(-0.004, 0.004)
        if (numero := ritmo.tomar(500 + i / fuente_fps + jitter)) is not None:
            numeros.append(numero)
    assert len(numeros) == pytest.approx(esperados * 10, abs=2)
    assert numeros == sorted(set(numeros))  # each slot once, increasing
    assert numeros[-1] == pytest.approx(150, abs=2)  # the grid keeps up with the real time


def test_ritmo_de_30_fps_toma_uno_de_cada_dos() -> None:
    ritmo = Ritmo(15)
    generador = np.random.default_rng(2)
    tomados = [
        i
        for i in range(300)
        if ritmo.tomar(7.3 + i / 30 + generador.uniform(-0.005, 0.005)) is not None
    ]
    assert {b - a for a, b in pairwise(tomados)} == {2}


def test_ritmo_salta_las_ranuras_de_una_webcam_detenida() -> None:
    ritmo = Ritmo(15)
    assert ritmo.tomar(10.0) == 0
    assert ritmo.tomar(10.0 + 1 / 15) == 1
    assert ritmo.tomar(12.0) == 30  # 2 s without frames
    assert ritmo.tomar(12.0 + 1 / 15) == 31


def test_ritmo_con_un_reloj_que_vuelve_atras_empieza_de_nuevo() -> None:
    ritmo = Ritmo(15)
    assert ritmo.tomar(10.0) == 0
    assert ritmo.tomar(3.0) == 0
    ritmo.reiniciar()
    assert ritmo.tomar(50.0) == 0


# ---------------------------------------------------------------- thread


def test_el_hilo_publica_y_se_cierra() -> None:
    publicados = threading.Event()
    publicadores: list[PublicadorFalso] = []

    def abrir(url: str, fps: float) -> PublicadorFalso:
        publicador = PublicadorFalso(url, fps)
        publicador.publicar = lambda imagen, instante: publicados.set()  # type: ignore[method-assign]
        publicadores.append(publicador)
        return publicador

    vivo = TransmisionEnVivo(permitida=lambda: True, abrir_publicador=abrir)
    vivo.iniciar()
    vivo.transmitir(URL, None, None, ModoVista.VIDEO)
    vivo.ofrecer(0.0, np.zeros((480, 640, 3), dtype=np.uint8))
    assert publicados.wait(2)
    vivo.cerrar()
    assert publicadores[0].cerrado
    assert publicadores[0].url == URL  # no credentials, no userinfo


def test_el_hilo_publica_el_cuadro_preparado_al_transmitir() -> None:
    publicados = threading.Event()

    def abrir(url: str, fps: float) -> PublicadorFalso:
        publicador = PublicadorFalso(url, fps)
        publicador.publicar = lambda imagen, instante: publicados.set()  # type: ignore[method-assign]
        return publicador

    vivo = TransmisionEnVivo(
        permitida=lambda: True, abrir_publicador=abrir, calentar=lambda a, b, c: None
    )
    vivo.iniciar()
    try:
        vivo.preparar()
        vivo.ofrecer(0.0, np.zeros((480, 640, 3), dtype=np.uint8))
        time.sleep(0.05)  # the worker keeps it
        inicio = time.perf_counter()
        vivo.transmitir(URL, None, None, ModoVista.VIDEO)
        assert publicados.wait(2)
        assert time.perf_counter() - inicio < 0.15  # not the idle worker's 0.2 s poll
    finally:
        vivo.cerrar()


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
