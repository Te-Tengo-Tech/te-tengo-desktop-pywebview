from itertools import pairwise
from pathlib import Path

import cv2
import numpy as np
import pytest

from te_tengo_captura.captura.fuentes import (
    CALIDAD_JPEG,
    Captador,
    FuenteArchivo,
    FuenteFalsa,
    FuenteWebcam,
    Muestreador,
    a_480p,
    preparar,
)


class Reloj:
    def __init__(self) -> None:
        self.ahora = 0.0

    def __call__(self) -> float:
        return self.ahora


def test_preparar_baja_a_480p_con_ancho_par_y_jpeg_80() -> None:
    imagen = np.random.default_rng(1).integers(0, 255, (1080, 1920, 3), dtype=np.uint8)
    fotograma = preparar(imagen, 1.25)
    assert fotograma.imagen.shape == (480, 854, 3)  # round(853.3 / 2) * 2
    assert fotograma.instante_ms == 1250
    assert fotograma.jpeg[:2] == b"\xff\xd8"
    # The pose is estimated on the decoded JPEG, as in the validation.
    decodificada = cv2.imdecode(np.frombuffer(fotograma.jpeg, np.uint8), cv2.IMREAD_COLOR)
    assert decodificada is not None
    assert np.array_equal(decodificada, fotograma.imagen)
    reducida = cv2.resize(imagen, (854, 480))
    _, esperado = cv2.imencode(".jpg", reducida, [cv2.IMWRITE_JPEG_QUALITY, CALIDAD_JPEG])
    assert fotograma.jpeg == esperado.tobytes()


def test_preparar_no_agranda_imagenes_pequenas() -> None:
    fotograma = preparar(np.zeros((240, 320, 3), dtype=np.uint8), 0.0)
    assert fotograma.imagen.shape == (240, 320, 3)


def test_muestrea_8_fps_de_una_fuente_de_30_fps() -> None:
    muestreador = Muestreador(8.0)
    tomados = [i / 30 for i in range(300) if muestreador.tomar(i / 30)]
    assert len(tomados) == 80  # 10 s
    assert tomados[:3] == [0.0, 4 / 30, 8 / 30]


def test_muestreo_igual_al_de_la_validacion() -> None:
    # The same rule as scripts/evaluar.py on a 25 fps file.
    muestreador, siguiente, esperados = Muestreador(8.0), 0.0, []
    for i in range(250):
        t = i / 25
        if t + 1e-9 >= siguiente:
            siguiente += 1 / 8
            esperados.append(t)
    assert [i / 25 for i in range(250) if muestreador.tomar(i / 25)] == esperados


def test_tras_un_corte_no_deja_pasar_una_rafaga() -> None:
    muestreador = Muestreador(8.0)
    assert muestreador.tomar(0.0)
    assert muestreador.tomar(5.0)
    assert not muestreador.tomar(5.03)
    assert muestreador.tomar(5.125)


def captador(fuente: FuenteFalsa, reloj: Reloj) -> Captador:
    return Captador(fuente, reloj=reloj, fps=8.0, segundos_desconexion=3.0, segundos_reapertura=2.0)


def test_captador_entrega_fotogramas_muestreados() -> None:
    reloj, fuente = Reloj(), FuenteFalsa(paso=1 / 30)
    c = captador(fuente, reloj)
    fotogramas = [f for _ in range(60) if (f := c.leer()) is not None]
    assert c.conectada is True
    assert len(fotogramas) == 16  # 2 s at 8 fps
    assert fotogramas[1].instante == pytest.approx(4 / 30)


def test_al_leer_ve_cada_cuadro_sin_cambiar_lo_que_se_clasifica() -> None:
    vistos: list[float] = []
    reloj = Reloj()
    sin_vista = captador(FuenteFalsa(paso=1 / 30), reloj)
    con_vista = Captador(
        FuenteFalsa(paso=1 / 30), reloj=reloj, fps=8.0, al_leer=lambda t, _: vistos.append(t)
    )
    a = [f for _ in range(60) if (f := sin_vista.leer()) is not None]
    b = [f for _ in range(60) if (f := con_vista.leer()) is not None]
    assert len(vistos) == 60  # every webcam frame, before the 8 fps sampling
    assert [(f.instante, f.jpeg) for f in a] == [(f.instante, f.jpeg) for f in b]


def test_un_error_en_al_leer_no_detiene_la_captura(caplog: pytest.LogCaptureFixture) -> None:
    def roto(instante: float, imagen: object) -> None:
        raise RuntimeError("vista en vivo rota")

    c = Captador(FuenteFalsa(paso=1 / 8), reloj=Reloj(), fps=8.0, al_leer=roto)
    assert c.leer() is not None
    assert "vista en vivo" in caplog.text


def test_a_480p() -> None:
    assert a_480p(np.zeros((720, 1280, 3), dtype=np.uint8)).shape == (480, 854, 3)
    pequena = np.zeros((480, 640, 3), dtype=np.uint8)
    assert a_480p(pequena) is pequena


def test_detecta_desconexion_tras_n_segundos_y_reconecta_sola() -> None:
    reloj, fuente = Reloj(), FuenteFalsa()
    c = captador(fuente, reloj)
    c.leer()
    assert c.conectada is True

    fuente.conectada = False
    for t in (0.5, 1.0, 2.0, 3.0):
        reloj.ahora = t
        assert c.leer() is None
        assert c.conectada is True  # a few failed reads are not a disconnection
    reloj.ahora = 3.5
    c.leer()
    assert c.conectada is False
    assert c.espera() == 2.0
    assert fuente.aperturas == 1

    fuente.conectada = True
    reloj.ahora = 4.0
    c.leer()
    assert fuente.aperturas == 1  # waits for the reopen interval
    reloj.ahora = 5.5
    c.leer()
    assert fuente.aperturas == 2
    assert c.conectada is True


def test_webcam_que_no_abre_queda_desconectada_y_reintenta() -> None:
    reloj, fuente = Reloj(), FuenteFalsa()
    fuente.conectada = False
    c = captador(fuente, reloj)
    assert c.leer() is None
    assert c.conectada is False
    reloj.ahora = 2.0
    c.leer()
    assert fuente.aperturas == 2


def test_buscar_de_nuevo_fuerza_la_reapertura() -> None:
    reloj, fuente = Reloj(), FuenteFalsa()
    fuente.conectada = False
    c = captador(fuente, reloj)
    c.leer()
    fuente.conectada = True
    c.buscar_de_nuevo()
    assert c.espera() == 0.0
    c.leer()
    assert fuente.aperturas == 2
    assert c.conectada is True
    c.cerrar()
    assert not fuente.abierta


@pytest.fixture
def video(tmp_path: Path) -> Path:
    ruta = tmp_path / "video.avi"
    escritor = cv2.VideoWriter(str(ruta), cv2.VideoWriter.fourcc(*"MJPG"), 20.0, (320, 240))
    for i in range(20):
        escritor.write(np.full((240, 320, 3), i * 10, dtype=np.uint8))
    escritor.release()
    return ruta


def test_fuente_archivo_usa_el_tiempo_del_video(video: Path) -> None:
    fuente = FuenteArchivo(video)
    assert fuente.abrir()
    instantes = []
    while (lectura := fuente.leer()) is not None:
        instantes.append(lectura[0])
    assert len(instantes) == 20
    assert instantes[:2] == [0.0, 0.05]
    assert fuente.agotada
    fuente.cerrar()


def test_fuente_archivo_repetida_sigue_creciendo(video: Path) -> None:
    fuente = FuenteArchivo(video, repetir=True)
    assert fuente.abrir()
    instantes = [lectura[0] for _ in range(45) if (lectura := fuente.leer()) is not None]
    assert len(instantes) == 45
    assert all(b > a for a, b in pairwise(instantes))
    assert instantes[20] == pytest.approx(1.0)


def test_fuente_archivo_inexistente(tmp_path: Path) -> None:
    fuente = FuenteArchivo(tmp_path / "no.avi")
    assert not fuente.abrir()
    assert fuente.leer() is None


def test_webcam_inexistente_no_abre() -> None:
    fuente = FuenteWebcam(97)
    assert not fuente.abrir()
    assert fuente.leer() is None
    fuente.cerrar()


def test_estado_desconocido_hasta_abrir_la_webcam() -> None:
    c = captador(FuenteFalsa(), Reloj())
    assert c.conectada is None


def test_fuente_archivo_en_tiempo_real_no_se_adelanta(video: Path) -> None:
    import time

    fuente = FuenteArchivo(video, tiempo_real=True)
    assert fuente.abrir()
    inicio = time.monotonic()
    for _ in range(3):
        fuente.leer()
    assert time.monotonic() - inicio >= 0.1  # third frame at 0.10 s
