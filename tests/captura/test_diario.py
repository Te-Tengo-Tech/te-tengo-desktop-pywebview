"""Advanced mode (US-32): the live log in plain language and the meters."""

import logging
from collections.abc import Iterator

import pytest

from te_tengo_captura.diario import Diario, ManejadorDiario, Narrador
from te_tengo_deteccion.clasificacion.estados import ClasificadorCinematico
from te_tengo_deteccion.clasificacion.umbrales import Umbrales
from te_tengo_deteccion.pose.schemas import Landmark, Pose
from tests.fabricas import CAYENDO, DE_PIE, TENDIDA


class Reloj:
    def __init__(self) -> None:
        self.ahora = 0.0

    def __call__(self) -> float:
        return self.ahora


@pytest.fixture
def diario() -> Iterator[Diario]:
    d = Diario()
    d.activo = True
    manejador = ManejadorDiario(d)
    raiz = logging.getLogger()
    raiz.addHandler(manejador)
    nivel = logging.getLogger("te_tengo_captura.diario").level
    logging.getLogger("te_tengo_captura.diario").setLevel(logging.INFO)
    yield d
    raiz.removeHandler(manejador)
    logging.getLogger("te_tengo_captura.diario").setLevel(nivel)


def narrar(diario: Diario, poses: list[tuple[float, Pose | None]]) -> tuple[Narrador, list[str]]:
    reloj = Reloj()
    narrador = Narrador(lambda: "c1", lambda: "Sala", lambda: "Webcam USB HD", reloj)
    clasificador = ClasificadorCinematico(Umbrales(velocidad_descenso_min=0.5))
    for instante, pose in poses:
        reloj.ahora = instante
        eventos = clasificador.actualizar(instante, pose)
        narrador.analizado(instante, pose, clasificador, eventos)
    return narrador, [linea.texto for linea in diario.desde("c1")]


def caida() -> list[tuple[float, Pose | None]]:
    secuencia: list[tuple[float, Pose | None]] = []
    t = 0.0
    for _ in range(12):  # standing for 1.5 s
        secuencia.append((t, DE_PIE))
        t += 0.125
    secuencia += [(t, CAYENDO), (t + 0.125, TENDIDA)]
    t += 0.25
    for _ in range(int(31 / 0.125)):  # on the floor until it is confirmed
        secuencia.append((t, TENDIDA))
        t += 0.125
    for _ in range(16):  # up again
        secuencia.append((t, DE_PIE))
        t += 0.125
    return secuencia


def test_una_caida_contada_en_lenguaje_sencillo(diario: Diario) -> None:
    narrador, lineas = narrar(diario, caida())
    assert lineas[0] == "Persona detectada en la Sala"
    assert "Bajó rápido la cadera (descenso por encima del umbral)" in lineas
    assert "Posible caída: esperando que quede en el suelo (1,48 s)" in lineas
    assert "Caída: quedó en el suelo. Aviso enviado a la familia" in lineas
    assert "Caída confirmada: sigue en el suelo después de 30 s" in lineas
    assert lineas[-1] == "Se levantó"
    lineas_completas = diario.desde("c1")
    caida_ = next(linea for linea in lineas_completas if linea.texto.startswith("Caída:"))
    assert (caida_.k, caida_.tono, caida_.icono) == ("evento", "caida", "warn")
    assert " WARN clasificador fase=CAIDA en_suelo=1 evento=caida aviso=encolado" in caida_.tecnica
    assert caida_.tecnica[:4].isdigit()  # ISO time first: «Ver línea técnica»
    assert narrador.medicion.fase == 0  # standing again


def test_medidores_durante_la_caida(diario: Diario) -> None:
    narrador, _ = narrar(diario, caida()[:14])
    m = narrador.medicion
    assert m.persona
    assert m.fase == 2  # «En el suelo»
    assert m.m3 is not None
    assert m.m3 >= 1
    assert set(m.visibilidad) == {"Nariz", "Hombros", "Caderas", "Tobillos"}
    assert set(m.esqueleto) >= {"h", "hL", "aR"}
    assert (m.umbral_angulo, m.umbral_razon, m.ventana_total, m.confirmacion) == (45, 1, 1.48, 30)


def test_sin_persona_y_descartes_sin_repetir(diario: Diario) -> None:
    sin_tobillos = Pose(
        tuple(
            Landmark(lm.x, lm.y, 0.1 if i in (27, 28) else lm.visibilidad)
            for i, lm in enumerate(DE_PIE.landmarks)
        ),
        DE_PIE.ancho,
        DE_PIE.alto,
    )
    poses: list[tuple[float, Pose | None]] = [(i * 0.125, sin_tobillos) for i in range(40)]
    poses += [(5 + i * 0.125, None) for i in range(24)]
    _, lineas = narrar(diario, poses)
    assert lineas.count("Imagen descartada: no se ven los tobillos") == 1  # at most every 10 s
    assert lineas[-1] == "Sin persona en la imagen"


def test_conexion_pausa_y_camara(diario: Diario) -> None:
    from datetime import UTC, datetime

    narrador = Narrador(lambda: "c1", lambda: "Dormitorio", lambda: "Logitech C920", Reloj())
    narrador.estado(True, True, None)
    narrador.estado(False, False, None)
    narrador.estado(True, True, datetime(2026, 9, 23, 16, 42, tzinfo=UTC))
    textos = [linea.texto for linea in diario.desde("c1")]
    assert textos[0] == "Se abrió la cámara del Dormitorio (Logitech C920)"
    assert "Cámara desconectada: revisa el cable USB" in textos
    assert "Sin internet. Los avisos esperan en la cola" in textos
    assert "Volvió internet. Se enviaron los avisos pendientes" in textos
    assert any(t.startswith("Cámara en pausa hasta las ") for t in textos)


def test_solo_con_el_modo_avanzado_y_en_memoria(diario: Diario) -> None:
    diario.activo = False
    _, lineas = narrar(diario, caida()[:3])
    assert lineas == []
    diario.activo = True
    narrar(diario, caida()[:3])
    assert diario.desde("c1")
    ultimo = diario.desde("c1")[-1].id
    assert diario.desde("c1", ultimo) == []
    diario.vaciar()
    assert diario.desde("c1") == []


def test_anillo_limitado() -> None:
    d = Diario(capacidad=3)
    d.activo = True
    for i in range(5):
        d.agregar("c", "programa", "", "monitor", f"l{i}", "x", "10:00:00")
    assert [linea.texto for linea in d.desde("c")] == ["l2", "l3", "l4"]
