import pytest

from te_tengo_deteccion.clasificacion.estados import (
    ClasificadorCinematico,
    Fase,
    TipoEvento,
    UmbralSinCalibrarError,
)
from te_tengo_deteccion.clasificacion.umbrales import Umbrales
from te_tengo_deteccion.pose.schemas import Landmark, Pose
from tests import fabricas

PASO = 0.1  # 10 fps


def reproducir(
    clasificador: ClasificadorCinematico, secuencia: list[tuple[float, Pose | None]]
) -> list[tuple[float, TipoEvento]]:
    eventos = []
    for instante, pose in secuencia:
        eventos += [(e.instante, e.tipo) for e in clasificador.actualizar(instante, pose)]
    return eventos


def de_pie(desde: float, hasta: float) -> list[tuple[float, Pose | None]]:
    n = round((hasta - desde) / PASO)
    return [(round(desde + i * PASO, 2), fabricas.DE_PIE) for i in range(n + 1)]


def test_caida_se_detecta_con_las_tres_condiciones(umbrales: Umbrales) -> None:
    c = ClasificadorCinematico(umbrales)
    eventos = reproducir(c, [*de_pie(0, 1.0), (1.1, fabricas.CAYENDO)])
    assert eventos == [(1.1, TipoEvento.CAIDA)]
    assert c.fase is Fase.EN_EL_SUELO


def test_caida_se_confirma_tras_30_s_en_el_suelo(umbrales: Umbrales) -> None:
    c = ClasificadorCinematico(umbrales)
    suelo = [(round(1.2 + i, 1), fabricas.TENDIDA) for i in range(31)]
    eventos = reproducir(c, [*de_pie(0, 1.0), (1.1, fabricas.CAYENDO), *suelo])
    assert eventos == [(1.1, TipoEvento.CAIDA), (31.2, TipoEvento.CAIDA_CONFIRMADA)]


def test_confirmacion_cuenta_aunque_no_se_vea_a_la_persona(umbrales: Umbrales) -> None:
    c = ClasificadorCinematico(umbrales)
    eventos = reproducir(c, [*de_pie(0, 1.0), (1.1, fabricas.CAYENDO), (31.1, None)])
    assert eventos[-1] == (31.1, TipoEvento.CAIDA_CONFIRMADA)


def test_levantarse_tras_la_caida_genera_recuperacion(umbrales: Umbrales) -> None:
    c = ClasificadorCinematico(umbrales)
    secuencia: list[tuple[float, Pose | None]] = [
        *de_pie(0, 1.0),
        (1.1, fabricas.CAYENDO),
        (5.0, fabricas.TENDIDA),
        (9.0, fabricas.DE_PIE),
        (9.5, fabricas.DE_PIE),
        (10.0, fabricas.DE_PIE),  # upright for 1 s
    ]
    assert reproducir(c, secuencia) == [(1.1, TipoEvento.CAIDA), (10.0, TipoEvento.RECUPERACION)]
    assert c.fase is Fase.NORMAL


def test_perdida_de_equilibrio_recuperada_es_movimiento_inestable(umbrales: Umbrales) -> None:
    c = ClasificadorCinematico(umbrales)
    eventos = reproducir(c, [*de_pie(0, 1.0), (1.1, fabricas.TAMBALEO), (1.5, fabricas.DE_PIE)])
    assert eventos == [(1.5, TipoEvento.MOVIMIENTO_INESTABLE)]


def test_inestable_que_termina_en_el_suelo_es_caida(umbrales: Umbrales) -> None:
    c = ClasificadorCinematico(umbrales)
    eventos = reproducir(c, [*de_pie(0, 1.0), (1.1, fabricas.TAMBALEO), (1.6, fabricas.TENDIDA)])
    assert eventos == [(1.6, TipoEvento.CAIDA)]


def test_inicio_sin_desenlace_vuelve_a_normal_sin_evento(umbrales: Umbrales) -> None:
    c = ClasificadorCinematico(umbrales)
    eventos = reproducir(c, [*de_pie(0, 1.0), (1.1, fabricas.TAMBALEO), (2.7, fabricas.TAMBALEO)])
    assert eventos == []
    assert c.fase is Fase.NORMAL


def test_agacharse_no_genera_eventos(umbrales: Umbrales) -> None:
    # Only M1: the hip drops quickly, but the body stays vertical.
    c = ClasificadorCinematico(umbrales)
    assert reproducir(c, [*de_pie(0, 1.0), (1.1, fabricas.AGACHADA), (1.5, fabricas.DE_PIE)]) == []


def test_inclinarse_no_genera_eventos(umbrales: Umbrales) -> None:
    # Only M2: the body tilts, but the hip does not drop.
    c = ClasificadorCinematico(umbrales)
    assert reproducir(c, [*de_pie(0, 1.0), (1.1, fabricas.INCLINADA), (1.5, fabricas.DE_PIE)]) == []


def test_marcha_normal_no_genera_eventos(umbrales: Umbrales) -> None:
    c = ClasificadorCinematico(umbrales)
    assert reproducir(c, de_pie(0, 10.0)) == []


def test_deteccion_no_confiable_tras_5_min_sin_fotogramas_validos(umbrales: Umbrales) -> None:
    c = ClasificadorCinematico(umbrales)
    secuencia: list[tuple[float, Pose | None]] = [(float(t), None) for t in range(0, 311)]
    assert reproducir(c, secuencia) == [(300.0, TipoEvento.DETECCION_NO_CONFIABLE)]


def test_aviso_no_confiable_se_reinicia_al_volver_a_ver_a_la_persona(umbrales: Umbrales) -> None:
    c = ClasificadorCinematico(umbrales)
    secuencia: list[tuple[float, Pose | None]] = [
        (0.0, fabricas.DE_PIE),
        (300.0, None),
        (301.0, fabricas.DE_PIE),
        (601.0, None),
    ]
    assert reproducir(c, secuencia) == [
        (300.0, TipoEvento.DETECCION_NO_CONFIABLE),
        (601.0, TipoEvento.DETECCION_NO_CONFIABLE),
    ]


def test_clasificador_exige_el_umbral_de_velocidad() -> None:
    with pytest.raises(UmbralSinCalibrarError):
        ClasificadorCinematico(Umbrales())


def test_pose_dudosa_no_declara_recuperacion(umbrales: Umbrales) -> None:
    # Lying person with poorly visible ankles: MediaPipe "invents" them in a position that
    # would make the person look standing. This must not be taken as a recovery.
    c = ClasificadorCinematico(umbrales)
    reproducir(c, [*de_pie(0, 1.0), (1.1, fabricas.CAYENDO)])
    falsa = list(fabricas.DE_PIE.landmarks)
    falsa[27] = falsa[28] = Landmark(falsa[27].x, falsa[27].y, 0.3)
    pose_dudosa = Pose(tuple(falsa), fabricas.ANCHO, fabricas.ALTO)
    assert c.actualizar(2.0, pose_dudosa) == []
    assert c.fase is Fase.EN_EL_SUELO


def test_pose_dudosa_puede_completar_una_caida(umbrales: Umbrales) -> None:
    # The speed is only measured with visible points, but the final posture (M3) may come
    # from a doubtful pose: a false alarm is preferable to missing a fall.
    c = ClasificadorCinematico(umbrales)
    dudosa = list(fabricas.TENDIDA.landmarks)
    dudosa[27] = dudosa[28] = Landmark(dudosa[27].x, dudosa[27].y, 0.4)
    tendida_dudosa = Pose(tuple(dudosa), fabricas.ANCHO, fabricas.ALTO)
    secuencia: list[tuple[float, Pose | None]] = [
        *de_pie(0, 1.0),
        (1.1, fabricas.TAMBALEO),
        (1.3, tendida_dudosa),
    ]
    assert reproducir(c, secuencia) == [(1.3, TipoEvento.CAIDA)]


def test_un_fotograma_erguido_suelto_no_es_recuperacion(umbrales: Umbrales) -> None:
    c = ClasificadorCinematico(umbrales)
    secuencia: list[tuple[float, Pose | None]] = [
        *de_pie(0, 1.0),
        (1.1, fabricas.CAYENDO),
        (3.0, fabricas.DE_PIE),  # single-frame error
        (3.1, fabricas.TENDIDA),
    ]
    assert reproducir(c, secuencia) == [(1.1, TipoEvento.CAIDA)]
    assert c.fase is Fase.EN_EL_SUELO


def test_caida_hacia_la_camara_con_cabeza_bajo_los_pies(umbrales: Umbrales) -> None:
    # Top-down view: when falling towards the camera the body appears foreshortened and almost
    # vertical, but the head ends up lower than the feet in the image.
    c = ClasificadorCinematico(umbrales)
    hacia_camara = fabricas.pose(cabeza=(320, 420), cadera=(320, 360), tobillos=(320, 300))
    eventos = reproducir(c, [*de_pie(0, 1.0), (1.2, hacia_camara)])
    assert eventos == [(1.2, TipoEvento.CAIDA)]


def test_tiempos_para_mostrar_el_avance(umbrales: Umbrales) -> None:
    c = ClasificadorCinematico(umbrales)
    reproducir(c, [*de_pie(0, 1.0), (1.1, fabricas.CAYENDO), (5.0, fabricas.TENDIDA)])
    tiempos = c.tiempos(6.1)
    assert tiempos.en_el_suelo == pytest.approx(5.0)
    assert tiempos.desde_inicio_caida is None
