import sys
from pathlib import Path

import pytest

from te_tengo_captura.config import Configuracion
from te_tengo_captura.estado import Entradas, derivar
from te_tengo_captura.ui.puente import Puente
from te_tengo_captura.ui.ventana import ALTO, ANCHO, WEB, VentanaEstado
from tests.captura.ui.webview_falso import WebviewFalso


@pytest.fixture
def webview(monkeypatch: pytest.MonkeyPatch) -> WebviewFalso:
    falso = WebviewFalso()
    monkeypatch.setitem(sys.modules, "webview", falso)
    return falso


def puente() -> Puente:
    return Puente(lambda: {}, lambda: None, lambda: True, lambda: True)


def test_ventana_de_960_x_640_sin_marco_ni_cambio_de_tamano(webview: WebviewFalso) -> None:
    VentanaEstado(puente())
    ventana = webview.ventanas[0]
    assert ventana.titulo == "Te Tengo Captura"
    assert Path(ventana.url or "") == WEB / "index.html"
    assert (ventana.opciones["width"], ventana.opciones["height"]) == (ANCHO, ALTO) == (960, 640)
    assert ventana.opciones["resizable"] is False
    assert ventana.opciones["frameless"] is True
    assert ventana.opciones["easy_drag"] is False
    assert ventana.opciones["hidden"] is True


def test_cerrar_oculta_en_la_bandeja_sin_salir(webview: WebviewFalso) -> None:
    ocultada = []
    estado = VentanaEstado(puente(), al_ocultar=lambda: ocultada.append(True), oculta=False)
    ventana = webview.ventanas[0]
    assert ventana.events.closing.disparar() == [False]  # the close is cancelled
    assert not ventana.visible
    assert ocultada == [True]
    estado.mostrar()
    assert ventana.visible
    estado.destruir()
    assert ventana.events.closing.disparar() == [True]  # «Salir» really closes
    assert ventana.destruida


def test_actualiza_la_pagina_solo_cuando_cargo(
    webview: WebviewFalso, configuracion: Configuracion
) -> None:
    estado = VentanaEstado(puente())
    ventana = webview.ventanas[0]
    entradas = Entradas(True, True, True, None, 2, 8, "Sala")
    agente = derivar(entradas, configuracion, "1.0.0")
    estado.actualizar(agente)
    assert ventana.scripts == []
    ventana.events.loaded.disparar()
    estado.actualizar(agente)
    assert ventana.scripts[0].startswith("window.ttg && window.ttg.actualizar(")


def test_ejecutar_abre_la_ventana_inicia_y_detiene_el_agente(
    webview: WebviewFalso, tmp_path: Path, configuracion: Configuracion
) -> None:
    from te_tengo_captura.ui.aplicacion import ejecutar

    class AgenteFalso:
        def __init__(self) -> None:
            self.eventos: list[str] = []
            self.oyentes: list[object] = []

        def estado(self) -> object:
            return derivar(Entradas(True, True, True, None, 2, 8, "Sala"), configuracion, "1.0.0")

        def suscribir(self, oyente: object) -> None:
            self.oyentes.append(oyente)

        def iniciar(self) -> None:
            self.eventos.append("iniciar")

        def detener(self) -> None:
            self.eventos.append("detener")

        def buscar_webcam(self) -> bool:
            return True

        def reintentar_ahora(self) -> bool:
            return True

    agente = AgenteFalso()
    ejecutar(agente)  # type: ignore[arg-type]
    assert webview.iniciado
    assert agente.eventos == ["iniciar", "detener"]
    assert len(agente.oyentes) == 1
    puente = webview.ventanas[0].opciones["js_api"]
    assert puente.estado()["situacion"] == "enviando"
    puente.cerrar()
    assert not webview.ventanas[0].visible
