import sys
from pathlib import Path

import pytest

from te_tengo_captura.ui import arranque
from te_tengo_captura.ui.arranque import DURACION_MINIMA_S, Paso, VentanaArranque, recorrer
from te_tengo_captura.ui.ventana import WEB
from tests.captura.test_agente import Escenario
from tests.captura.ui.webview_falso import WebviewFalso


class Reloj:
    def __init__(self) -> None:
        self.ahora = 0.0
        self.esperas: list[float] = []

    def __call__(self) -> float:
        return self.ahora

    def esperar(self, segundos: float) -> None:
        self.esperas.append(segundos)
        self.ahora += segundos


def test_muestra_cada_paso_cuando_el_anterior_esta_listo() -> None:
    reloj = Reloj()
    listo = {"webcam": False}
    mostrados: list[tuple[int, int, float]] = []

    def mostrar(pct: int, paso: int) -> None:
        mostrados.append((pct, paso, reloj.ahora))
        if pct == 54:
            listo["webcam"] = False

    def webcam() -> bool:
        listo["webcam"] = reloj.ahora >= 1.0  # the webcam answers after 1 s
        return listo["webcam"]

    pasos = [
        Paso(22, 0, lambda: True),
        Paso(54, 1, webcam),
        Paso(86, 2, lambda: True),
        Paso(100, 2, lambda: True),
    ]
    recorrer(pasos, mostrar, reloj, reloj.esperar)
    assert [(p, t) for p, t, _ in mostrados] == [(22, 0), (54, 1), (86, 2), (100, 2)]
    assert mostrados[2][2] == pytest.approx(1.0, abs=0.1)  # within one polling interval
    assert reloj.ahora == pytest.approx(DURACION_MINIMA_S)  # the fade out starts at 2.06 s


def test_conserva_el_ritmo_del_prototipo_aunque_todo_este_listo() -> None:
    reloj = Reloj()
    momentos: list[float] = []
    pasos = [
        Paso(22, 0, lambda: True, desde_s=0.08),
        Paso(54, 1, lambda: True, desde_s=0.72),
        Paso(86, 2, lambda: True, desde_s=1.34),
        Paso(100, 2, lambda: True, desde_s=1.82),
    ]
    recorrer(pasos, lambda p, t: momentos.append(reloj.ahora), reloj, reloj.esperar)
    assert momentos == pytest.approx([0.08, 0.72, 1.34, 1.82])
    assert reloj.ahora == pytest.approx(2.06)


def test_un_paso_que_no_termina_no_bloquea_el_arranque() -> None:
    reloj = Reloj()
    recorrer([Paso(54, 1, lambda: False, limite_s=5.0)], lambda p, t: None, reloj, reloj.esperar)
    assert reloj.ahora == pytest.approx(5.0, abs=0.1)


def test_pasos_reales_del_agente(tmp_path: Path, configuracion: object) -> None:
    e = Escenario(tmp_path, configuracion)  # type: ignore[arg-type]
    pasos = arranque.pasos(e.agente)
    assert [(p.porcentaje, p.indice_texto, p.desde_s) for p in pasos] == [
        (22, 0, 0.08),
        (54, 1, 0.72),
        (86, 2, 1.34),
        (100, 2, 1.82),
    ]
    webcam, conexion = pasos[1].listo, pasos[2].listo
    assert not webcam()
    assert not conexion()
    e.backend.quitar_consentimiento()
    e.agente.reintentar_ahora()
    assert conexion()
    assert webcam()  # not opened because capture is not allowed: nothing to wait for
    e.backend.permitir()
    e.agente.reintentar_ahora()
    assert not webcam()
    e.agente.bucle.paso()
    assert webcam()
    e.agente.detener()


def test_ventana_de_arranque(monkeypatch: pytest.MonkeyPatch) -> None:
    webview = WebviewFalso()
    monkeypatch.setitem(sys.modules, "webview", webview)
    inicio = VentanaArranque("1.0.0")
    ventana = webview.ventanas[0]
    assert Path(ventana.url or "") == WEB / "arranque.html"
    assert (ventana.opciones["width"], ventana.opciones["height"]) == (480, 300)
    assert ventana.opciones["frameless"] is True
    assert ventana.opciones["resizable"] is False
    assert ventana.opciones["background_color"] == "#4A2A85"
    assert "x" not in ventana.opciones  # pywebview centers it
    ventana.events.loaded.disparar()
    assert inicio.esperar_carga(0)
    inicio.mostrar(54, 1)
    assert ventana.scripts == ['window.ttg && window.ttg.arranque(54, 1, "1.0.0")']
    inicio.cerrar(esperar=lambda s: None)
    assert ventana.destruida
