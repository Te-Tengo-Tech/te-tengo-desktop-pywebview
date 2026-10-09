import numpy as np
import pytest

from te_tengo_captura.backend.modelos import ModoVista
from te_tengo_captura.captura.fuentes import Imagen
from te_tengo_captura.captura.postura import BLANCO, DURAZNO, MORADO, componer
from te_tengo_deteccion.pose.schemas import TOTAL_LANDMARKS, Landmark, Pose

ANCHO, ALTO = 640, 480


def persona(visibilidad: float = 0.9) -> Pose:
    """A standing person spread over the frame: every landmark at a distinct point."""
    puntos = [(0.3 + 0.4 * (i % 5) / 4, 0.1 + 0.8 * i / TOTAL_LANDMARKS) for i in range(33)]
    return Pose(tuple(Landmark(x, y, visibilidad) for x, y in puntos), ANCHO, ALTO)


def camara(semilla: int, alto: int = ALTO, ancho: int = ANCHO) -> Imagen:
    """A frame of a «home»: noise, so any camera pixel that leaks would be noticed."""
    generador = np.random.default_rng(semilla)
    return generador.integers(0, 256, (alto, ancho, 3), dtype=np.uint8)


def colores(imagen: Imagen) -> set[tuple[int, int, int]]:
    unicos = np.unique(imagen.reshape(-1, 3), axis=0)
    return {(int(b), int(g), int(r)) for b, g, r in unicos}


def test_solo_postura_no_contiene_pixeles_de_la_camara() -> None:
    pose = persona()
    una = componer(camara(1), pose, ModoVista.SOLO_POSTURA)
    otra = componer(camara(2), pose, ModoVista.SOLO_POSTURA)
    # Only the brand colours, and the same picture whatever the camera saw.
    assert colores(una) == {MORADO, BLANCO, DURAZNO}
    assert np.array_equal(una, otra)


def test_solo_postura_sin_persona_es_un_fondo_liso() -> None:
    imagen = componer(camara(3), None, ModoVista.SOLO_POSTURA)
    assert imagen.shape == (ALTO, ANCHO, 3)
    assert colores(imagen) == {MORADO}


def test_solo_postura_no_dibuja_puntos_poco_visibles() -> None:
    imagen = componer(camara(4), persona(visibilidad=0.2), ModoVista.SOLO_POSTURA)
    assert colores(imagen) == {MORADO}


def test_video_publica_el_fotograma_tal_cual() -> None:
    fotograma = camara(5)
    imagen = componer(fotograma, persona(), ModoVista.VIDEO)
    assert np.array_equal(imagen, fotograma)


def test_video_con_postura_dibuja_sobre_una_copia() -> None:
    fotograma = camara(6)
    original = fotograma.copy()
    imagen = componer(fotograma, persona(), ModoVista.VIDEO_CON_POSTURA)
    assert np.array_equal(fotograma, original)  # the capture loop's frame is untouched
    distintos = np.any(imagen != fotograma, axis=2)
    assert 0 < distintos.mean() < 0.2  # the skeleton, and the room around it
    assert {BLANCO, DURAZNO, MORADO} <= colores(imagen[distintos])


def test_video_con_postura_sin_persona_es_el_fotograma() -> None:
    fotograma = camara(7)
    assert np.array_equal(componer(fotograma, None, ModoVista.VIDEO_CON_POSTURA), fotograma)


@pytest.mark.parametrize("modo", list(ModoVista))
def test_las_dimensiones_son_pares_para_h264(modo: ModoVista) -> None:
    imagen = componer(camara(8, alto=481, ancho=641), persona(), modo)
    assert imagen.shape == (480, 640, 3)
    assert imagen.flags.c_contiguous
