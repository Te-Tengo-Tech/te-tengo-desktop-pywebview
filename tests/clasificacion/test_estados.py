import pytest

from detection_worker.clasificacion.estados import (
    ClasificadorCinematico,
    Fase,
    TipoEvento,
    UmbralSinCalibrarError,
)
from detection_worker.clasificacion.umbrales import Umbrales
from detection_worker.pose.schemas import Pose
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
    eventos = reproducir(
        c,
        [*de_pie(0, 1.0), (1.1, fabricas.CAYENDO), (5.0, fabricas.TENDIDA), (9.0, fabricas.DE_PIE)],
    )
    assert eventos == [(1.1, TipoEvento.CAIDA), (9.0, TipoEvento.RECUPERACION)]
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
    # Solo M1: la cadera baja rápido, pero el cuerpo sigue vertical.
    c = ClasificadorCinematico(umbrales)
    assert reproducir(c, [*de_pie(0, 1.0), (1.1, fabricas.AGACHADA), (1.5, fabricas.DE_PIE)]) == []


def test_inclinarse_no_genera_eventos(umbrales: Umbrales) -> None:
    # Solo M2: el cuerpo se inclina, pero la cadera no baja.
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
