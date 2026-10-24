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


# ---------------------------------------------------------------------- R9: slow falls


def tramo(desde: float, hasta: float, pose: Pose | None) -> list[tuple[float, Pose | None]]:
    n = round((hasta - desde) / PASO)
    return [(round(desde + i * PASO, 2), pose) for i in range(n)]


def deslizarse(desde: float, segundos: float) -> list[tuple[float, Pose | None]]:
    """Slides down from standing to sitting on the floor, slowly and with the torso upright."""
    n = round(segundos / PASO)
    secuencia: list[tuple[float, Pose | None]] = []
    for i in range(1, n + 1):
        f = i / n
        secuencia.append(
            (
                round(desde + i * PASO, 2),
                fabricas.pose(
                    cabeza=(320, 100 + 110 * f),
                    cadera=(320, 220 + 110 * f),
                    tobillos=(320 + 120 * f, 340),
                ),
            )
        )
    return secuencia


CALIBRADOS = Umbrales(velocidad_descenso_min=0.01)
SIN_R9 = CALIBRADOS.model_copy(update={"descenso_caida_lenta_min": 1e9})


def test_caida_lenta_deslizarse_y_quedar_tendida() -> None:
    # Sliding down a chair or a wall for 3 s, sitting 2 s and slumping back: the hip never
    # drops while the body is tilted, so R4 alone misses it.
    secuencia = [
        *de_pie(0, 2.0),
        *deslizarse(2.0, 3.0),
        *tramo(5.1, 7.0, fabricas.SENTADA_EN_EL_SUELO),
        *tramo(7.0, 12.0, fabricas.TENDIDA_SIN_BAJAR),
    ]
    assert reproducir(ClasificadorCinematico(SIN_R9), secuencia) == []

    c = ClasificadorCinematico(CALIBRADOS)
    eventos = []
    for instante, pose in secuencia:
        eventos += c.actualizar(instante, pose)
    assert [(e.instante, e.tipo) for e in eventos] == [(9.0, TipoEvento.CAIDA)]
    assert eventos[0].parametros["caida_lenta"] == 1.0
    assert eventos[0].parametros["descenso"] == pytest.approx(110 / 240, abs=1e-3)
    assert c.fase is Fase.EN_EL_SUELO


def test_caida_lenta_tras_arrodillarse(umbrales: Umbrales) -> None:
    # Kneeling looks upright, but the reference is still the standing hip of the last 10 s.
    sin_r4 = umbrales.model_copy(update={"velocidad_descenso_min": 100.0})
    secuencia = [
        *de_pie(0, 1.0),
        *tramo(1.1, 6.0, fabricas.ARRODILLADA),
        *tramo(6.0, 9.0, fabricas.TENDIDA_SIN_BAJAR),
    ]
    assert reproducir(ClasificadorCinematico(sin_r4), secuencia) == [(8.0, TipoEvento.CAIDA)]


def test_caida_lenta_sin_pose_un_rato_y_confirmacion() -> None:
    # Frames without a pose do not interrupt the count; the fall is declared on the next pose
    # and then follows the usual path to the confirmation (R6).
    c = ClasificadorCinematico(CALIBRADOS)
    secuencia = [
        *de_pie(0, 1.0),
        *tramo(1.1, 3.0, fabricas.SENTADA_EN_EL_SUELO),
        *tramo(3.0, 3.5, fabricas.TENDIDA_SIN_BAJAR),
        *tramo(3.5, 6.0, None),  # MediaPipe loses the person lying on the floor
        (6.0, fabricas.TENDIDA_SIN_BAJAR),
        *tramo(6.1, 36.1, None),
    ]
    assert reproducir(c, secuencia) == [
        (6.0, TipoEvento.CAIDA),
        (36.0, TipoEvento.CAIDA_CONFIRMADA),
    ]


def test_tenderse_en_la_cama_no_es_caida() -> None:
    # The hip ends about 0.2 lengths below its standing height: a bed or a sofa, not the floor.
    secuencia = [
        *de_pie(0, 2.0),
        *tramo(2.1, 5.0, fabricas.SENTADA_EN_LA_CAMA),
        *tramo(5.0, 60.0, fabricas.EN_LA_CAMA),
    ]
    assert reproducir(ClasificadorCinematico(CALIBRADOS), secuencia) == []


def test_tenderse_en_el_suelo_mucho_despues_de_estar_de_pie_no_es_caida_lenta() -> None:
    # Sitting on the floor (which looks upright) for longer than the window: the reference is
    # the sitting hip, and lying back from it does not drop the hip enough.
    secuencia = [
        *de_pie(0, 1.0),
        *tramo(1.1, 15.0, fabricas.SENTADA_EN_EL_SUELO),
        *tramo(15.0, 25.0, fabricas.TENDIDA_SIN_BAJAR),
    ]
    assert reproducir(ClasificadorCinematico(CALIBRADOS), secuencia) == []


def test_estar_tendida_menos_de_la_permanencia_no_es_caida_lenta() -> None:
    # Lying back for 1.5 s and sitting up again (a pose that is not horizontal restarts the
    # count), then lying again for 1.5 s.
    secuencia = [
        *de_pie(0, 1.0),
        *tramo(1.1, 3.0, fabricas.SENTADA_EN_EL_SUELO),
        *tramo(3.0, 4.5, fabricas.TENDIDA_SIN_BAJAR),
        *tramo(4.5, 5.0, fabricas.SENTADA_EN_EL_SUELO),
        *tramo(5.0, 6.5, fabricas.TENDIDA_SIN_BAJAR),
        *tramo(6.5, 8.0, fabricas.SENTADA_EN_EL_SUELO),
    ]
    assert reproducir(ClasificadorCinematico(CALIBRADOS), secuencia) == []


def test_caida_lenta_tras_la_ventana_de_reaccion(umbrales: Umbrales) -> None:
    # R4 starts (M1 and M2) but the body becomes horizontal after the 1.48 s window: R9 still
    # declares the fall once the body has been horizontal for 2 s.
    tambaleo_bajo = fabricas.pose(
        cabeza=(420, 280), cadera=(330, 330), tobillos=(300, 340), extra=(330, 180)
    )  # θ ≈ 27° (M2) with a raised arm that keeps P < 1 (no M3)
    secuencia = [
        *de_pie(0, 1.0),
        *tramo(1.1, 3.0, tambaleo_bajo),
        *tramo(3.0, 6.0, fabricas.TENDIDA_SIN_BAJAR),
    ]
    sin_r9 = umbrales.model_copy(update={"descenso_caida_lenta_min": 1e9})
    assert reproducir(ClasificadorCinematico(sin_r9), secuencia) == []
    assert reproducir(ClasificadorCinematico(umbrales), secuencia) == [(5.0, TipoEvento.CAIDA)]


def test_umbrales_de_caida_lenta_por_defecto() -> None:
    u = Umbrales()
    assert (u.descenso_caida_lenta_min, u.ventana_caida_lenta_s, u.permanencia_caida_lenta_s) == (
        0.4,
        10.0,
        2.0,
    )
