import sys
from pathlib import Path

import pytest

from te_tengo_captura.config import Configuracion
from te_tengo_captura.estado import Entradas, derivar
from te_tengo_captura.ui.puente import Puente
from te_tengo_captura.ui.ventana import ALTO, ANCHO, WEB, VentanaEstado
from tests.captura.ui.pystray_falso import PystrayFalso
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
    webview: WebviewFalso, configuracion: Configuracion, monkeypatch: pytest.MonkeyPatch
) -> None:
    pystray = PystrayFalso()
    monkeypatch.setitem(sys.modules, "pystray", pystray)
    from te_tengo_captura.ui import arranque
    from te_tengo_captura.ui.aplicacion import ejecutar

    class AgenteFalso:
        version = "1.0.0"

        def __init__(self) -> None:
            self.eventos: list[str] = []
            self.oyentes: list[object] = []

        config = configuracion

        def estado(self) -> object:
            return derivar(Entradas(True, True, True, None, 2, 8, "Sala"), configuracion, "1.0.0")

        def publicar_estado(self) -> None:
            self.eventos.append("publicar")

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
    pasos = [arranque.Paso(22, 0, lambda: True), arranque.Paso(100, 2, lambda: True)]
    monkeypatch.setattr(arranque, "pasos", lambda _: pasos)
    monkeypatch.setattr(arranque, "DURACION_MINIMA_S", 0.0)
    monkeypatch.setattr(arranque, "SALIDA_S", 0.0)
    ejecutar(agente)  # type: ignore[arg-type]
    assert webview.iniciado
    assert agente.eventos == ["iniciar", "publicar", "detener"]
    assert len(agente.oyentes) == 3  # window, tray icon and notifications
    inicio, estado = webview.ventanas
    assert inicio.destruida  # the splash gives way to the status window
    assert inicio.scripts[-1] == "window.ttg && window.ttg.arranqueFin()"
    assert estado.visible
    puente = estado.opciones["js_api"]
    assert puente.estado()["situacion"] == "enviando"
    bandeja = pystray.iconos[0]
    assert not bandeja.corriendo  # stopped when the app ended
    puente.cerrar()
    assert not estado.visible
    assert bandeja.notificaciones == [
        (
            "Te Tengo Captura sigue funcionando en segundo plano",
            "Sigue enviando el video de la cámara. Ábrelo desde su ícono, junto al reloj.",
        )
    ]
    assert bandeja.menu is not None
    abrir, salir = bandeja.menu.items
    abrir.accion()
    assert estado.visible
    salir.accion()
    assert estado.destruida
